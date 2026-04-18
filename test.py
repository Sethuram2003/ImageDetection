import cv2
import numpy as np
import matplotlib.pyplot as plt
import warnings
from sklearn.cluster import DBSCAN
import os

warnings.filterwarnings('ignore')

class VanishingPointDetector:
    """
    Detects vanishing points in images, focusing on robust detection in scenery.
    AI-generated images often exhibit multiple inconsistent vanishing points,
    while real photos often have fewer, stronger ones.
    """
    
    def __init__(self, image_path):
        """
        Initialize the detector with an image path.
        """
        self.image_path = image_path
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found at {image_path}")
            
        self.image = cv2.imread(image_path)
        self.image_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        self.height, self.width = self.image.shape[:2]
        self.gray = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        
    def detect_lines(self):
        """
        Detect line segments in the image using Canny and Probabilistic Hough Line Transform.
        Probabilistic Hough is generally more accurate for finding line segments.
        """
        scale_factor = 1.0
        working_width = self.width
        working_height = self.height
        
        # Optimize size for standard processing speed
        target_dim = 1200
        if max(self.width, self.height) > target_dim:
            scale_factor = target_dim / max(self.width, self.height)
            working_width = int(self.width * scale_factor)
            working_height = int(self.height * scale_factor)
            working_image = cv2.resize(self.gray, (working_width, working_height))
        else:
            working_image = self.gray.copy()
        
        # Blurring and Contrast Enhancement (CLAHE)
        blurred = cv2.GaussianBlur(working_image, (5, 5), 1.0)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(blurred)
        
        # Optimized Canny thresholds for structured scenes
        edges = cv2.Canny(enhanced, 50, 150)
        
        # --- Change 2: Use Probabilistic Hough Line Transform ---
        # HoughLinesP returns segments [x1, y1, x2, y2], which are more precise.
        line_segments = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi / 180,
            threshold=50,                  # Accumulator threshold
            minLineLength=int(working_width * 0.1), # Min segment length (10% of width)
            maxLineGap=20                   # Max gap to connect segments
        )
        
        if line_segments is None or len(line_segments) == 0:
            return np.array([])
        
        # Reshape to Nx4
        line_segments = line_segments.squeeze(axis=1)
        
        # Scale back to original coordinates
        if scale_factor < 1.0:
            line_segments = (line_segments / scale_factor).astype(int)
        
        return line_segments
    
    def line_intersection(self, line1, line2):
        """
        Find the intersection point of two line segments.
        """
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2
        
        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        
        if abs(denom) < 1e-6:  # Parallel lines
            return None
        
        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        
        px = x1 + t * (x2 - x1)
        py = y1 + t * (y2 - y1)
        
        return (px, py)
    
    def find_vanishing_points(self, lines, distance_threshold_ratio=0.02):
        """
        Find vanishing points by analyzing line intersections and clustering.
        The distance threshold is now scaled to image size.
        """
        if len(lines) < 3:
            return []
        
        # --- Change 1: Scale DBSCAN Threshold ---
        # Calculate dynamic threshold based on the larger image dimension (2%)
        scaled_distance_threshold = int(max(self.width, self.height) * distance_threshold_ratio)
        print(f"   Using dynamic DBSCAN distance threshold: {scaled_distance_threshold} pixels (ratio {distance_threshold_ratio})")

        intersections = []
        
        # Computing intersections from line segments
        print(f"   Computing intersections from {len(lines)} line segments...")
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                intersection = self.line_intersection(lines[i], lines[j])
                
                if intersection is not None:
                    px, py = intersection
                    
                    # Intersections are valid if within extended bounds (helpful for off-screen VPs)
                    if (-self.width * 2.0 <= px <= self.width * 3.0 and 
                        -self.height * 2.0 <= py <= self.height * 3.0):
                        intersections.append([px, py])
        
        print(f"   Found {len(intersections)} intersection points")
        
        if len(intersections) < 3:
            return []
        
        intersections = np.array(intersections)
        
        # Cluster using dynamic threshold
        vanishing_points = self._cluster_intersections_dbscan(intersections, scaled_distance_threshold)
        
        # --- Change 3: Post-Clustering Refinement ---
        # Refine by relative significance and potential merging
        refined_vps = self._refine_vanishing_points(vanishing_points, scaled_distance_threshold)
        
        return refined_vps
    
    def _cluster_intersections_dbscan(self, intersections, distance_threshold):
        """
        Cluster intersection points using DBSCAN with a dynamic threshold.
        """
        if len(intersections) == 0:
            return []
        
        if len(intersections) == 1:
            return [(tuple(intersections), 1)] # Single intersection, low score
        
        # min_samples is dynamic based on total intersections (0.5%)
        min_samples = max(3, int(len(intersections) * 0.005))
        
        clustering = DBSCAN(eps=distance_threshold, min_samples=min_samples).fit(intersections)
        labels = clustering.labels_
        
        unique_labels = set(labels)
        clusters = []
        
        for label in unique_labels:
            if label == -1:  # Noise points
                continue
            cluster_points = intersections[labels == label]
            mean_point = np.mean(cluster_points, axis=0)
            significance = len(cluster_points)
            clusters.append((tuple(mean_point), significance))
        
        # Sort by significance (descending)
        sorted_clusters = sorted(clusters, key=lambda x: x[1], reverse=True)
        
        return sorted_clusters

    def _refine_vanishing_points(self, vanishing_points, distance_threshold, significance_ratio=0.15):
        """
        Refines detected vanishing points by merging duplicates and filtering insignificant ones.
        
        - Merges VPs that are closer than the distance_threshold.
        - Filters VPs that are significantly weaker than the strongest VP.
        """
        if not vanishing_points:
            return []

        # 1. Signficance Filtering (Top N, typically strongest for sceneray)
        max_vps_to_consider = 5
        candidate_vps = vanishing_points[:max_vps_to_consider]
        
        # 2. Merge nearby points (Iterative approach)
        merged_vps = []
        while candidate_vps:
            current_vp, current_sig = candidate_vps.pop(0)
            vp_x1, vp_y1 = current_vp
            
            close_vps = []
            remaining_vps = []
            
            for other_vp, other_sig in candidate_vps:
                vp_x2, vp_y2 = other_vp
                # Euclidean distance
                dist = np.sqrt((vp_x1 - vp_x2)**2 + (vp_y1 - vp_y2)**2)
                
                if dist < distance_threshold:
                    close_vps.append((other_vp, other_sig))
                else:
                    remaining_vps.append((other_vp, other_sig))
            
            if close_vps:
                # Weighted average based on significance
                all_close = [(current_vp, current_sig)] + close_vps
                total_sig = sum(sig for _, sig in all_close)
                
                avg_x = sum(vp[0] * sig for vp, sig in all_close) / total_sig
                avg_y = sum(vp[1] * sig for vp, sig in all_close) / total_sig
                
                merged_vps.append(((avg_x, avg_y), total_sig))
            else:
                merged_vps.append((current_vp, current_sig))
                
            candidate_vps = remaining_vps

        # Sort again after merging
        merged_vps = sorted(merged_vps, key=lambda x: x[1], reverse=True)
        
        # 3. Relative Significance Filtering
        if len(merged_vps) > 1:
            strongest_sig = merged_vps[0][1]
            final_vps = [merged_vps[0]]
            
            # Keep others only if they are stronger than ratio (e.g., 15% of strongest)
            for vp, sig in merged_vps[1:]:
                if sig > strongest_sig * significance_ratio:
                    final_vps.append((vp, sig))
            return final_vps
        
        return merged_vps

    def visualize_results(self, lines, vanishing_points, save_path=None):
        """
        Visualize detected lines and vanishing points on the image.
        """
        vis_image = self.image_rgb.copy()
        
        # Colors for visualization
        colors = [(255, 0, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255)]
        
        # Draw all significant lines (green)
        for line in lines:
            x1, y1, x2, y2 = line
            
            x1_clip = max(0, min(self.width - 1, x1))
            y1_clip = max(0, min(self.height - 1, y1))
            x2_clip = max(0, min(self.width - 1, x2))
            y2_clip = max(0, min(self.height - 1, y2))
            
            cv2.line(vis_image, (x1_clip, y1_clip), (x2_clip, y2_clip), 
                    color=(0, 255, 0), thickness=2, lineType=cv2.LINE_AA)
        
        # Subplots configuration
        fig = plt.figure(figsize=(18, 8))
        
        # Original image
        ax1 = plt.subplot(1, 3, 1)
        ax1.imshow(self.image_rgb)
        ax1.set_title('Original Image', fontsize=14, fontweight='bold')
        ax1.axis('off')
        
        # Lines visualization
        ax2 = plt.subplot(1, 3, 2)
        ax2.imshow(vis_image)
        ax2.set_title(f'Detected Line Segments ({len(lines)})', fontsize=14, fontweight='bold')
        ax2.axis('off')
        
        # Vanishing points visualization
        ax3 = plt.subplot(1, 3, 3)
        vp_image = self.image_rgb.copy()
        
        for idx, (vp_info, significance) in enumerate(vanishing_points):
            vp_x, vp_y = vp_info
            color = colors[idx % len(colors)]
            
            # Visual marker (circle) at VP
            if 0 <= vp_x < self.width and 0 <= vp_y < self.height:
                cv2.circle(vp_image, (int(vp_x), int(vp_y)), 15, color, -1)
                cv2.circle(vp_image, (int(vp_x), int(vp_y)), 20, color, 2)
                
            # Text label
            text_pos = (int(vp_x) + 20, int(vp_y) - 20)
            # Adjust label position if point is near border
            if vp_x > self.width * 0.8: text_pos = (int(vp_x) - 100, int(vp_y) - 20)
            if vp_y < self.height * 0.2: text_pos = (int(vp_x) + 20, int(vp_y) + 40)
            
            cv2.putText(vp_image, f'VP{idx+1}', text_pos,
                       cv2.FONT_HERSHEY_SIMPLEX, 1.2, color, 3, lineType=cv2.LINE_AA)
            
            # --- Draw converging lines to each VP (extended green lines) ---
            # Extend detected segments to show convergence
            for line in lines:
                x1, y1, x2, y2 = line
                # Simple line towards VP
                cv2.line(vp_image, (int(x1), int(y1)), (int(vp_x), int(vp_y)), 
                        color=(100, 255, 100), thickness=1, lineType=cv2.LINE_AA)
        
        ax3.imshow(vp_image)
        ax3.set_title(f'Vanishing Points ({len(vanishing_points)})', 
                     fontsize=14, fontweight='bold')
        ax3.axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"✓ Visualization saved to {save_path}")
        
        plt.show()
    
    def detect(self, visualize=True, save_visualization=None):
        """
        Main detection pipeline.
        """
        print("=" * 60)
        print("VANISHING POINT DETECTION ANALYSIS")
        print("=" * 60)
        print(f"Image: {self.image_path}")
        print(f"Image size: {self.width} x {self.height} pixels")
        
        # Step 1: Detect line segments
        print("\n[1/3] Detecting lines in image...")
        lines = self.detect_lines()
        print(f"✓ Detected {len(lines)} line segments")
        
        # Step 2: Find vanishing points
        print("\n[2/3] Finding vanishing points...")
        vanishing_points = self.find_vanishing_points(lines)
        print(f"✓ Detected {len(vanishing_points)} refined vanishing point(s)")
        
        if len(vanishing_points) > 0:
            for i, (vp_info, significance) in enumerate(vanishing_points):
                vp_x, vp_y = vp_info
                print(f"   VP{i+1}: ({vp_x:.1f}, {vp_y:.1f}) | Score: {significance}")
        else:
            print("   No significant vanishing points detected.")
        
        # Step 3: Classify image
        # Basic classification - 1 VP in structured scenery often strong confidence
        # For scenery, VP count > 2 is often suspect or complex geometry.
        vp_count = len(vanishing_points)
        print("\n" + "=" * 60)
        print("SCENERY ANALYSIS SUMMARY:")
        print("=" * 60)
        print(f"Detected Vanishing Points: {vp_count}")
        if vp_count == 1:
            print("Strong, clean geometric structure (typical of single road/corridor).")
        elif vp_count == 2:
            print("Clear geometric structure (e.g., street corner, multi-point perspective).")
        elif vp_count > 2:
            print(f"Complex geometric scene or potential inconsistencies (count {vp_count}).")
        else:
            print("Scene lacks strong converging parallel lines.")
        print("=" * 60)
        
        # Visualization
        if visualize and len(lines) > 0:
            print("\nGenerating visualization...")
            self.visualize_results(lines, vanishing_points, save_visualization)
        
        # Simplify return object (VPs with scores)
        final_vps_list = [vp for vp in vanishing_points]
        
        return {
            'image_path': self.image_path,
            'lines_detected': len(lines),
            'vanishing_points_scored': vanishing_points,
            'vanishing_points': final_vps_list,
            'vp_count': vp_count
        }


def main():
    """
    Main function to run vanishing point detection on image(s).
    """
    
    # Define the image path - Example: place an image in an 'images' folder
    # Or replace this string with your direct path: image_path = 'C:/path/to/my_image.jpg'
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Assuming images are in a folder 'images' relative to this script
    image_path = os.path.join(script_dir, 'images', 'camera1.jpeg') 
    
    # --- Check if image exists before running ---
    if not os.path.exists(image_path):
        print(f"\nError: Image not found at {image_path}")
        print("Please ensure the image file is present at the location or update 'image_path'.\n")
        return

    # Create detector and run analysis
    try:
        detector = VanishingPointDetector(image_path)
        
        results = detector.detect(
            visualize=True,
            save_visualization=os.path.join(script_dir, 'vanishing_points.png') # Optional saving
        )
        
    except FileNotFoundError as e:
        print(e)
    except Exception as e:
        print(f"An error occurred during detection: {e}")

if __name__ == "__main__":
    main()