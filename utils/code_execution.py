import nbformat
from nbconvert.preprocessors import ExecutePreprocessor
import tempfile
import os
import re
from typing import List, Tuple, Union



CODE_BLOCK_PATTERN = r"```[ \t]*(\w+)?[ \t]*\r?\n(.*?)\r?\n[ \t]*```"


def extract_code(
    text: Union[str, List], pattern: str = CODE_BLOCK_PATTERN, detect_single_line_code: bool = False
) -> List[Tuple[str, str]]:
    """Extract code from a text.

    Args:
        text (str or List): The content to extract code from. The content can be
            a string or a list, as returned by standard GPT or multimodal GPT.
        pattern (str, optional): The regular expression pattern for finding the
            code block. Defaults to CODE_BLOCK_PATTERN.
        detect_single_line_code (bool, optional): Enable the new feature for
            extracting single line code. Defaults to False.

    Returns:
        list: A list of tuples, each containing the language and the code.
          If there is no code block in the input text, the language would be "unknown".
          If there is code block but the language is not specified, the language would be "".
    """
    if not detect_single_line_code:
        match = re.findall(pattern, text, flags=re.DOTALL)
        return match if match else [("unknown", text)]

    # Extract both multi-line and single-line code block, separated by the | operator
    # `([^`]+)`: Matches inline code.
    code_pattern = re.compile(CODE_BLOCK_PATTERN + r"|`([^`]+)`")
    code_blocks = code_pattern.findall(text)

    # Extract the individual code blocks and languages from the matched groups
    extracted = []
    for lang, group1, group2 in code_blocks:
        if group1:
            extracted.append((lang.strip(), group1.strip()))
        elif group2:
            extracted.append(("", group2.strip()))

    return extracted

def evaluate_python_code(code: str, authorized_imports: list[str]) -> str:
    """
    Safely executes Python code in an isolated Jupyter notebook environment
    Returns the output as a string
    """
    
    # Create new notebook with the code
    notebook = nbformat.v4.new_notebook()
    notebook['cells'] = [nbformat.v4.new_code_cell(code)]
    
    # Save notebook to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ipynb', delete=False) as tmp:
        nbformat.write(notebook, tmp)
        tmp_name = tmp.name

    try:
        # Execute the notebook
        with open(tmp_name, 'r') as f:
            nb = nbformat.read(f, as_version=4)
        
        ep = ExecutePreprocessor(timeout=30, kernel_name='python3')
        ep.preprocess(nb, {'metadata': {'path': './'}})

        # Extract output
        output = ""
        for cell in nb.cells:
            if cell.cell_type == 'code' and cell.outputs:
                for output_item in cell.outputs:
                    if output_item.output_type == 'stream':
                        output += output_item.text
                    elif output_item.output_type == 'execute_result':
                        output += str(output_item.data.get('text/plain', ''))
        
        return output.strip()
        
    finally:
        os.unlink(tmp_name) 