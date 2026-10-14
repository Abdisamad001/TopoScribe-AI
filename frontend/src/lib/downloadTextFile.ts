export async function downloadTextFile(filename: string, content: string): Promise<boolean> {
    if (typeof window === 'undefined') return false;

    const picker = (window as Window & {
        showSaveFilePicker?: (options: {
            suggestedName?: string;
            types?: { description: string; accept: Record<string, string[]> }[];
        }) => Promise<FileSystemFileHandle>;
    }).showSaveFilePicker;

    if (typeof picker === 'function') {
        try {
            const handle = await picker({
                suggestedName: filename,
                types: [
                    {
                        description: 'Markdown',
                        accept: { 'text/markdown': ['.md'], 'text/plain': ['.md', '.txt'] },
                    },
                ],
            });
            const writable = await handle.createWritable();
            await writable.write(content);
            await writable.close();
            return true;
        } catch (error) {
            // User cancelled the save dialog — stop. Other errors fall through.
            if (error instanceof DOMException && error.name === 'AbortError') return false;
        }
    }

    try {
        // octet-stream avoids some Chrome "insecure download" blocks on plain HTTP.
        const blob = new Blob([content], { type: 'application/octet-stream' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.rel = 'noopener';
        link.style.display = 'none';
        document.body.appendChild(link);
        link.click();
        window.setTimeout(() => {
            URL.revokeObjectURL(url);
            link.remove();
        }, 1500);
        return true;
    } catch {
        return false;
    }
}
