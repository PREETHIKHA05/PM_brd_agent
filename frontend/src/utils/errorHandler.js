export const getErrorMessage = (err, defaultMessage = 'An error occurred') => {
    if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (typeof detail === 'string') {
            return detail;
        } else if (Array.isArray(detail)) {

            return detail.map(e => e.msg).join(', ');
        } else if (typeof detail === 'object') {

            return JSON.stringify(detail);
        }
    }
    return defaultMessage;
};
