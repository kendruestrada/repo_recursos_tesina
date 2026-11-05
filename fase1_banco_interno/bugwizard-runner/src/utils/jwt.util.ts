export const parseJwt = (token: string) => {
  try {
    const base64Url = token.split('.')[1];
    if (base64Url) {
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      const jsonParsed = JSON.parse(jsonPayload);
      return jsonParsed;
    }
  } catch (e) {
    console.error('Error al parsear JWT:', e);
    return null;
  }
};