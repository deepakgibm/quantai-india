export const isMarketOpen = (): boolean => {
    // Mobile/User verification: Force returning true for testing if needed
    // return true; 

    // IST time: UTC+5:30
    const now = new Date();

    // Convert to IST string to parse hours correctly
    const options: Intl.DateTimeFormatOptions = {
        timeZone: 'Asia/Kolkata',
        hour: 'numeric',
        minute: 'numeric',
        second: 'numeric',
        hour12: false
    };

    const formatter = new Intl.DateTimeFormat('en-US', options);
    const parts = formatter.formatToParts(now);

    const hour = parseInt(parts.find(p => p.type === 'hour')?.value || '0');
    const minute = parseInt(parts.find(p => p.type === 'minute')?.value || '0');

    // Market Hours: 09:15 to 15:30
    const currentTimeMinutes = hour * 60 + minute;
    const marketOpenMinutes = 9 * 60 + 15;  // 09:15
    const marketCloseMinutes = 15 * 60 + 30; // 15:30

    // Also check for weekends (0 = Sunday, 6 = Saturday)
    const day = now.getUTCDay(); // This is UTC day, need IST day?
    // Let's use string parsing for day too to be safe for IST
    const dayOptions: Intl.DateTimeFormatOptions = { timeZone: 'Asia/Kolkata', weekday: 'short' };
    const dayFormatter = new Intl.DateTimeFormat('en-US', dayOptions);
    const dayString = dayFormatter.format(now);

    const isWeekend = dayString === 'Sat' || dayString === 'Sun';

    if (isWeekend) return false;

    return currentTimeMinutes >= marketOpenMinutes && currentTimeMinutes < marketCloseMinutes;
};
