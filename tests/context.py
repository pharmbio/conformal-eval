import os

# calculate absolute paths for loading test-files and writing output
resource_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources")
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_output")

# Create the output_dir if it doesn't exist yet
os.makedirs(output_dir,exist_ok=True)