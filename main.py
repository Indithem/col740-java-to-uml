from tree_sitter import Language, Parser, Query, QueryCursor, Node, Tree
import tree_sitter
import tree_sitter_java
import os
from pprint import pprint
from collections import defaultdict
import networkx
from typing import List

JAVA_LANGUAGE = Language(tree_sitter_java.language())
JAVA_PARSER = Parser(JAVA_LANGUAGE)

def pretty_print_tree(node: tree_sitter.Node, level=0):
    indent = "  " * level
    text = node.text.decode()
    text = "TOO LONG, omitting..." if len(text) > 50 else text
    print(f"{indent}{node.type} [{node.start_point} - {node.end_point}] \"{text}\"")
    for child in node.children:
        pretty_print_tree(child, level + 1)

def pretty_print_captures(captures):
    for (id, nodes) in captures.items():
        print(id, ":")
        for n in nodes:
            pretty_print_tree(n)

def get_tree(src_file: str) -> Tree:
    with open(src_file, 'rb') as f:
        return JAVA_PARSER.parse(f.read())

def test_query(file_name):
    with open(file_name, 'rb') as f:
        tree = JAVA_PARSER.parse(f.read())
    query = Query(
        JAVA_LANGUAGE,
        """
        (class_declaration
            name: (identifier) @name
            body: (class_body
                (method_declaration
                    name: (identifier) @method_names)))
        """
    )
    qc = QueryCursor(query)
    captures = qc.captures(tree.root_node)
    pretty_print_captures(captures)

GRAPH = networkx.MultiGraph()

def construct_graph(src_path: str, src_project_name: str):
    GRAPH.clear()
    for root, _, files in os.walk(src_path):
        for file in files:
            if file.endswith(".java"):
                absolute_path = os.path.join(root, file)
                rel_file = absolute_path.rsplit(src_project_name.replace('.', '/')+'/', 1)
                assert len(rel_file)== 2
                rel_file = rel_file[1] \
                    # .rstrip('.java')
                GRAPH.add_node(rel_file,
                    tree = get_tree(absolute_path).root_node,
                    class_name = rel_file.rsplit('/', 1)[-1].rsplit('.java', 1)[0]
                )

    import_query = QueryCursor(Query(
        JAVA_LANGUAGE,
        f"""
        (import_declaration
            (scoped_identifier
                (scoped_identifier) @package_name
                (#match? @package_name "^{src_project_name}")
            ) @import_nodes)
        """
    ))

    for file_name, attrs in list(GRAPH.nodes(data=True)):
        captures: dict[str, List[Node]] = defaultdict(list)
        captures.update(import_query.captures(attrs['tree']))
        for imports in captures['import_nodes']:
            package = imports.child_by_field_name('scope').text.decode()
            name = imports.child_by_field_name('name').text.decode()
            subpackage = package.split(src_project_name+'.', 1)[1]
            GRAPH.add_edge(file_name, f"{subpackage}/{name}.java", type="import module")

    for file_name, attrs in list(GRAPH.nodes(data=True)):

        # TODO: Problem when multiple classes in single file
        query = QueryCursor(Query(
            JAVA_LANGUAGE,
            f"""
            (class_declaration
                name: (identifier) @name
                (#eq? @name "{attrs['class_name']}")
                body: (class_body
                    (field_declaration)* @field_declarations
                    (method_declaration
                        name: (identifier)* @method_names)))
            """
        ))

        captures: dict[str, List[Node]] = defaultdict(list)
        captures.update(query.captures(attrs['tree']))

        items: List[str] = []
        for fields in captures['field_declarations']:
            type_name = fields.child_by_field_name('type').text.decode()
            field_names = [i.text.decode().split('=', 1)[0].strip() for i in fields.children_by_field_name('declarator')]
            items.extend([f"{type_name} {field_name}" for field_name in field_names])
        GRAPH.nodes[file_name]["fields"] = items

        items: List[str] = [i.text.decode() for i in captures['method_names']]
        GRAPH.nodes[file_name]["methods"] = items


    # pprint(dict(GRAPH.nodes(data=True)))
    # pprint(list(GRAPH.edges(data=True)))

def construct_puml(file_name="diagram.puml"):
    with open(file_name, 'w') as f:

        f.write("@startuml\n")

        # Map file_path to class_name for easier lookup
        class_name_map = {node_id: data.get('class_name', node_id) for node_id, data in GRAPH.nodes(data=True)}

        # Class definitions
        for node_id, node_attrs in GRAPH.nodes(data=True):
            # class_name = node_attrs.get('class_name', node_id)
            f.write(f"class {class_name_map[node_id]} {{\n")

            fields = node_attrs.get('fields', [])
            for field in fields:
                # Assuming public for now. field is "type name"
                parts = field.split()
                if len(parts) >= 2:
                    field_type = parts[0]
                    field_name = " ".join(parts[1:])
                    f.write(f"  + {field_name} : {field_type}\n")
                else:
                    f.write(f"  + {field}\n")


            methods = node_attrs.get('methods', [])
            for method in methods:
                f.write(f"  + {method}()\n")

            f.write("}\n")

        # Relationships
        for u, v, data in GRAPH.edges(data=True):
            u_class = class_name_map.get(u, u)
            v_class = class_name_map.get(v, v)
            if data.get('type') == 'import module':
                f.write(f"{u_class} ..> {v_class}\n")

        f.write("@enduml\n")



if __name__ == "__main__":
    SRC_FOLDER = './examples/spring-petclinic/src/main/java/org/springframework/samples/petclinic/'
    SRC_PROJECT_NAME = 'org.springframework.samples.petclinic'
    construct_graph(SRC_FOLDER, SRC_PROJECT_NAME)
    construct_puml()

    # files = [
    #     "examples/hello_world.java",
    #     "examples/spring-petclinic/src/main/java/org/springframework/samples/petclinic/owner/Owner.java",
    #     "./examples/spring-petclinic/src/main/java/org/springframework/samples/petclinic/vet/Vets.java",
    # ]
    # for f in files:
    #     print("testing on file", f)
    #     # test_query(f)
    #     # pretty_print_tree(get_tree(f).root_node)
