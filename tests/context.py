import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# calculate absolute paths for loading test-files and writing output
resource_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")

# Create the output_dir (and sub-dirs) if they don't exist yet
os.makedirs(os.path.join(output_dir,'clf'),exist_ok=True)
os.makedirs(os.path.join(output_dir,'reg'),exist_ok=True)