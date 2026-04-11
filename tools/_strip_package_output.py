from pathlib import Path

p = Path("ai_stack/langgraph_runtime_executor.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
i0 = next(i for i, l in enumerate(lines) if l.startswith("    def _package_output"))
replacement = '''    def _package_output(self, state: RuntimeTurnState) -> RuntimeTurnState:
        from ai_stack.langgraph_runtime_package_output import package_runtime_graph_output

        return package_runtime_graph_output(
            state, graph_name=self.graph_name, graph_version=self.graph_version
        )

'''
new_lines = lines[:i0] + [replacement]
p.write_text("".join(new_lines), encoding="utf-8")
print("trimmed from line", i0 + 1)
