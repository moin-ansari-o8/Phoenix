import ast
import os


def sort_methods_and_dicts_in_file(file_path):
    with open(file_path, "r") as f:
        file_content = f.read()
    tree = ast.parse(file_content)

    def sort_dict_content(node):
        """Sort dictionary entries alphabetically by their keys."""
        if isinstance(node, ast.Dict):
            sorted_items = sorted(
                zip(node.keys, node.values),
                key=lambda item: ast.unparse(item[0]) if item[0] else "",
            )
            return ast.Dict(
                keys=[item[0] for item in sorted_items],
                values=[item[1] for item in sorted_items],
            )
        return node

    def sort_list_content(node):
        """Sort list elements alphabetically."""
        if isinstance(node, ast.List):
            sorted_elements = sorted(node.elts, key=lambda elt: ast.unparse(elt))
            return ast.List(elts=sorted_elements, ctx=node.ctx)
        return node

    def process_body(body):
        """Sort methods in the body and format lists and dictionaries."""
        methods = []
        other_members = []
        for item in body:
            if isinstance(item, ast.FunctionDef):
                for node in ast.walk(item):
                    if isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name) and isinstance(
                                node.value, ast.Dict
                            ):
                                node.value = sort_dict_content(node.value)
                            elif isinstance(target, ast.Name) and isinstance(
                                node.value, ast.List
                            ):
                                node.value = sort_list_content(node.value)
                methods.append(item)
            else:
                other_members.append(item)
        methods.sort(key=lambda m: m.name)
        return other_members + methods

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            node.body = process_body(node.body)
    new_file_path = os.path.splitext(file_path)[0] + "_sort.py"
    with open(new_file_path, "w") as f:
        f.write(ast.unparse(tree))
    print(f"Sorted file created: {new_file_path}")


file_path = "E:\\STDY\\GIT_PROJECTS\\Phoenix\\TimeBased.py"
sort_methods_and_dicts_in_file(file_path)
