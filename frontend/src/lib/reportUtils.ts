/** Copy text; works even when Clipboard API is blocked (plain HTTP, some WebViews). */
export async function copyTextToClipboard(text: string): Promise<boolean> {
    if (typeof window === 'undefined') return false;
    try {
        if (navigator.clipboard?.writeText) {
            await navigator.clipboard.writeText(text);
            return true;
        }
    } catch {
        // fall through to execCommand
    }
    try {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.left = '-9999px';
        document.body.appendChild(ta);
        ta.select();
        const ok = document.execCommand('copy');
        document.body.removeChild(ta);
        return ok;
    } catch {
        return false;
    }
}

/** Copy clean text  */
export function stripMarkdown(md: string): string {
    if (!md) return '';
    return md
        .replace(/#{1,6}\s?/g, '')
        .replace(/\*\*/g, '')
        .replace(/\*/g, '')
        .replace(/`{3}[\s\S]*?`{3}/g, '')
        .replace(/`/g, '')
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
        .replace(/\|/g, ' ')
        .replace(/-{3,}/g, '')
        .trim();
}
