"""This is the CLI version of how to generate a HTML report 
"""

import argparse,sys
from _html import generate_html

class CustomArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # Custom error message with padding
        sys.stderr.write('\n' + '*' * 70 + '\n\n')
        sys.stderr.write(f"Error: {message}\n\n")
        sys.stderr.write('*' * 70 + '\n\n')
        self.print_help()
        sys.exit(2)

def main():
    # Initialize the parser
    parser = CustomArgumentParser(description="Generate a Model report for a CPSign model. Optionally include a `validation file` generated by `cpsign validate` or `cpsign crossvalidate` that include performance data for the model.")
    
    # Add possible arguments 
    parser.add_argument("-mf","--model-file", required=True, help="Path to the model file")
    parser.add_argument("-vf","--validation-file", required=False, help="Path to the optional validation file", default=None)
    parser.add_argument("-of","--output-file", required=False, help="Path to where to save the generated HTML page", default='model_report.html')
    parser.add_argument("-if","--info-file", required=False, help="Path to a file with extra information about the model, can include html-tags for better formatting", default=None)
    
    # Parse the arguments
    args = parser.parse_args()
    
    # Call the main function with the parsed arguments
    try:
        generate_html(args.model_file, args.output_file, args.validation_file, args.info_file)
    except Exception as e:
        sys.stderr.write(f'\nError: {e}\n\n')
        sys.exit(2)

if __name__ == "__main__":
    main()