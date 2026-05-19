import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Components } from "react-markdown";

const codeBlockStyle = {
  borderRadius: "0.375rem",
  fontSize: "0.75rem",
  margin: "0.5rem 0",
  padding: "0.75rem",
};

const markdownComponents: Components = {
  code({ className, children }) {
    const language = /language-([^\s]+)/.exec(className || "")?.[1];
    const text = String(children).replace(/\n$/, "");
    const isBlock = language !== undefined || text.includes("\n");

    if (isBlock) {
      return (
        <SyntaxHighlighter
          style={oneDark}
          language={language ?? "text"}
          PreTag="div"
          customStyle={codeBlockStyle}
        >
          {text}
        </SyntaxHighlighter>
      );
    }

    return (
      <code className="bg-muted px-1 py-0.5 rounded text-xs font-mono">
        {children}
      </code>
    );
  },
  pre({ children }) {
    return <>{children}</>;
  },
};

export function MarkdownContent({ content }: { content: string }) {
  return (
    <div className="prose prose-sm prose-invert max-w-none break-words [&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_h1]:text-base [&_h2]:text-sm [&_h3]:text-sm [&_h1]:font-bold [&_h2]:font-bold [&_h3]:font-semibold [&_ul]:pl-4 [&_ol]:pl-4 [&_li]:my-0.5 [&_p]:my-1 [&_strong]:font-bold">
      <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
    </div>
  );
}
