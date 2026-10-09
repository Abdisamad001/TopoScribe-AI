'use client';

import { useState } from 'react';
import { Copy, Terminal, Check } from 'lucide-react';
import { copyTextToClipboard } from '@/lib/reportUtils';

const KEYWORDS = [
    'version', 'hostname', 'interface', 'no', 'ip', 'address', 'shutdown',
    'router', 'network', 'area', 'end', 'write', 'memory', 'building', 'configuration',
];

function highlightLine(line: string) {
    if (!line) return <br />;
    if (line.trim().startsWith('!')) {
        return <span className="cisco-line--comment">{line}</span>;
    }
    const prompt = line.match(/^(\S+#)(.*)/);
    if (prompt) {
        return (
            <>
                <span className="cisco-line--prompt">{prompt[1]}</span>
                <span className="cisco-line--rest">{prompt[2]}</span>
            </>
        );
    }
    return (
        <span>
            {line.split(/(\s+)/).map((part, index) => {
                if (/^(\d{1,3}\.){3}\d{1,3}(\/\d+)?$/.test(part)) {
                    return <span key={index} className="cisco-line--ip">{part}</span>;
                }
                if (/^(Ethernet|FastEthernet|GigabitEthernet|Serial|Vlan)\d+/i.test(part)) {
                    return <span key={index} className="cisco-line--iface">{part}</span>;
                }
                if (KEYWORDS.includes(part.toLowerCase())) {
                    return <span key={index} className="cisco-line--kw">{part}</span>;
                }
                if (/^\d+(\.\d+)?$/.test(part)) {
                    return <span key={index} className="cisco-line--num">{part}</span>;
                }
                return <span key={index}>{part}</span>;
            })}
        </span>
    );
}

function cleanConfig(code: string): string {
    return code
        .split('\n')
        .filter(
            (line) =>
                !line.includes('Building configuration...') &&
                !line.includes('[OK]') &&
                !line.includes('show running-config') &&
                !line.includes('write memory'),
        )
        .map((line) => line.replace(/^\S+#\s*/, ''))
        .join('\n')
        .trim();
}

/** Cisco IOS config block shown inside the report viewer. */
export default function CiscoTerminal({ code }: { code: string }) {
    const [copied, setCopied] = useState(false);
    const deviceName = code.match(/^(\S+)#/)?.[1] || 'Device';

    const handleCopy = async () => {
        const ok = await copyTextToClipboard(cleanConfig(code));
        if (!ok) {
            alert('Could not copy. Try HTTPS, allow clipboard access, or select the text manually.');
            return;
        }
        setCopied(true);
        window.setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div className="cisco-terminal">
            <div className="cisco-terminal__header">
                <div className="cisco-terminal__title">
                    <Terminal size={18} />
                    <span className="cisco-terminal__device">{deviceName}</span>
                    <span className="cisco-terminal__hint">(CISCO IOS)</span>
                </div>
                <button type="button" onClick={handleCopy} className="cisco-terminal__copy">
                    {copied ? <Check size={14} /> : <Copy size={14} />}
                    {copied ? 'Copied!' : 'Copy Config'}
                </button>
            </div>
            <div className="cisco-terminal__body">
                {code.split('\n').map((line, i) => (
                    <div key={i} className="cisco-terminal__line">
                        {highlightLine(line)}
                    </div>
                ))}
            </div>
        </div>
    );
}
