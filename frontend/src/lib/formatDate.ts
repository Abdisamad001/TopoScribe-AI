export function formatDateTime(iso: string): string {
    try {
        return new Date(iso).toLocaleString();
    } catch {
        return iso;
    }
}


export function formatRelativeTime(iso: string): string {
    const deltaSec = Math.round((new Date(iso).getTime() - Date.now()) / 1000);
    const abs = Math.abs(deltaSec);
    const rtf = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });
    if (abs < 60) return rtf.format(Math.round(deltaSec), 'second');
    if (abs < 3600) return rtf.format(Math.round(deltaSec / 60), 'minute');
    if (abs < 86400) return rtf.format(Math.round(deltaSec / 3600), 'hour');
    if (abs < 86400 * 30) return rtf.format(Math.round(deltaSec / 86400), 'day');
    return rtf.format(Math.round(deltaSec / (86400 * 30)), 'month');
}
