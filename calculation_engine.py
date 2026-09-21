class CalculationEngine:
    @staticmethod
    def calculate_dimension_weight(length, breadth, height, num_boxes):
        """
        Formula: Dimension Weight = (Length × Breadth × Height ÷ 27000) × 6 × Number of Boxes
        """
        try:
            # Ensure float/int
            l = float(length)
            b = float(breadth)
            h = float(height)
            boxes = float(num_boxes)
            
            dim_weight = (l * b * h / 27000.0) * 6.0 * boxes
            return round(dim_weight, 2)
        except (ValueError, TypeError):
            return 0.0
