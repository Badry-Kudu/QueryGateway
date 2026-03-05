import CodeMirror from "@uiw/react-codemirror";
import { sql, StandardSQL } from "@codemirror/lang-sql";
import { oneDark } from "@codemirror/theme-one-dark";

interface SqlEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  height?: string;
  readOnly?: boolean;
}

export function SqlEditor({
  value,
  onChange,
  placeholder = "SELECT * FROM table WHERE column = :param",
  height = "200px",
  readOnly = false,
}: SqlEditorProps) {
  return (
    <div className="overflow-hidden rounded-md border">
      <CodeMirror
        value={value}
        height={height}
        theme={oneDark}
        extensions={[sql({ dialect: StandardSQL })]}
        onChange={onChange}
        placeholder={placeholder}
        readOnly={readOnly}
        basicSetup={{
          lineNumbers: true,
          foldGutter: true,
          highlightActiveLine: true,
          autocompletion: true,
        }}
      />
    </div>
  );
}
