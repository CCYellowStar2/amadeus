import React, { useState, useEffect, useRef } from 'react';
import AnsiToHtml from 'ansi-to-html';
import './Terminal.css';

const converter = new AnsiToHtml({
  fg: '#d4d4d4',
  bg: '#1e1e1e',
  newline: false,
  escapeXML: true,
});

interface TerminalProps {
  isVisible: boolean;
}

const Terminal: React.FC<TerminalProps> = ({ isVisible }) => {
  const [logs, setLogs] = useState<string[]>([]);
  const logsEndRef = useRef<null | HTMLDivElement>(null);

  useEffect(() => {
    if (window.api) {
      const cleanup = window.api.receive('backend-log', (log: string) => {
        const decodedLog = decodeURIComponent(escape(log));
        setLogs((prevLogs) => [...prevLogs, decodedLog]);
      });

      return cleanup;
    }
  }, []);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'auto' });
  }, [logs]);

  return (
    <div className={`terminal-modal ${isVisible ? 'visible' : ''}`}>
      <div className="terminal-container">
        <pre className="logs">
          {logs.map((log, index) => (
            <span key={index} dangerouslySetInnerHTML={{ __html: converter.toHtml(log) }} />
          ))}
          <div ref={logsEndRef} />
        </pre>
      </div>
    </div>
  );
};

export default Terminal; 