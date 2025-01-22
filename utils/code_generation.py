import ast
from typing import Any, List, OrderedDict
from caseconverter import pascalcase
import astor
import json
import isort
from isort import Config
from datamodel_code_generator import DataModelType, PythonVersion
from datamodel_code_generator.model import get_data_model_types
from datamodel_code_generator.parser.jsonschema import JsonSchemaParser


def json_schema_to_code(json_schema: str):
    data_model_types = get_data_model_types(
        DataModelType.PydanticV2BaseModel,
        target_python_version=PythonVersion.PY_311
    )
    parser = JsonSchemaParser(
    json_schema,
    data_model_type=data_model_types.data_model,
    data_model_root_type=data_model_types.root_model,
    data_model_field_type=data_model_types.field_model,
    data_type_manager_type=data_model_types.data_type_manager,
    dump_resolve_reference_action=data_model_types.dump_resolve_reference_action,
                        )
    result = parser.parse()

    return result


def get_args_type_from_function(function: dict):
    """Generates a Pydantic model name for function parameters"""
    if 'title' in function['parameters']:
        return function['parameters']['title']
    
    return pascalcase(function['name']) + 'Model'

def get_args_type(tool: dict):
    """Similar to get_args_type_from_function but for tool objects"""
    if 'title' in tool['function']['parameters']:
        return tool['function']['parameters']['title']
    
    title = pascalcase(tool['function']['name']) + 'Model'
    return title

def get_definitions(tool: dict):
    """Converts JSON schema of tool parameters into Pydantic model definitions"""
    code = json_schema_to_code(json.dumps(tool['function']['parameters']))
    if 'title' in tool['function']['parameters']:
        return code
    
    else:
        return code.replace(' Model(', f' {get_args_type(tool)}(')

def get_fn_str(function: dict, return_args: bool = False):
    """Generates function stub with proper type hints"""
    return f"def {function['name']}(args: {get_args_type_from_function(function)}):\n    # implementation left out for brevity\n    {'return args' if return_args else 'pass'}"

def get_fn_call_example_str(function: dict):
    return f"""{function['name']}({get_args_type_from_function(function)}(APPROPRIATE_ARGS))"""

def get_fn_names(tools: list[dict]):
    return ", ".join([tool['function']['name'] for tool in tools])

def get_code(tools: List[Any], return_args: bool = False):
    """
    Generates complete Python code including:
    - Pydantic models for parameter validation
    - Function stubs for each tool
    - Properly formatted and sorted imports
    """
    codes = [get_definitions(tool) for tool in tools]

    fns = []
    for tool in tools:
        fn_def = get_fn_str(tool['function'], return_args)

        fns.append(fn_def)
        codes.append(fn_def)

    return isort.code(remove_duplicate_imports("\n\n".join(codes)), config=Config(profile="black"))

def remove_duplicate_imports(source):
    """
    Analyzes AST to remove duplicate import statements while preserving order
    and handling both regular imports and from-imports
    """
    # Parse the source code into an AST
    tree = ast.parse(source)

    # Track unique imports
    unique_imports = OrderedDict()
    unique_from_imports = OrderedDict()

    # Collect all import nodes
    import_nodes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_nodes.append(node)

    # Process regular imports (import x)
    for node in import_nodes:
        if isinstance(node, ast.Import):
            for name in node.names:
                import_key = (name.name, name.asname)
                if import_key not in unique_imports:
                    unique_imports[import_key] = node

    # Process from imports (from x import y)
    for node in import_nodes:
        if isinstance(node, ast.ImportFrom):
            module = node.module if node.module else ''
            for name in node.names:
                from_key = (module, name.name, name.asname)
                if from_key not in unique_from_imports:
                    unique_from_imports[from_key] = node

    # Create new tree with only unique imports
    new_body = []
    
    # Add unique regular imports
    for node in unique_imports.values():
        new_body.append(node)
    
    # Add unique from imports
    for node in unique_from_imports.values():
        if node not in new_body:
            new_body.append(node)

    # Add all non-import nodes
    for node in tree.body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            new_body.append(node)

    # Create new tree
    new_tree = ast.Module(body=new_body, type_ignores=[])

    # Convert back to source code
    new_source = astor.to_source(new_tree)

    return new_source

def is_valid_tool_call(code: str, tools: List[Any]):
    """
    Validates if a code snippet is calling one of the defined tools
    Returns the function name if valid, None otherwise
    """
    fn_names = [tool['function']['name'] for tool in tools]

    for fn_name in fn_names:
        if code.startswith(fn_name+'('):
            return fn_name
    return None 