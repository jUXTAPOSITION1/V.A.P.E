"""
Verify VAPE build pipeline by printing a success message.

This script is used to test the GitHub Actions pipeline after enabling the
"Allow GitHub Actions to create and approve pull requests" setting in the repository.

Assumptions:
- The script is executed within the VAPE repository's GitHub Actions pipeline.
- The pipeline has the necessary permissions to execute the script.

Returns:
- None
"""

import logging

def main() -> None:
    """
    Print a success message to verify the VAPE build pipeline.
    
    Returns:
    - None
    """
    try:
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        
        # Print the success message
        logging.info("VAPE build pipeline verified")
        
    except Exception as e:
        # Log any exceptions that occur during execution
        logging.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()