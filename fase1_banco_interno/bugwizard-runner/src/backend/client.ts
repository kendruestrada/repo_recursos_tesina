export class BackendClient {
  constructor(
    private readonly baseUrl: string,
    private readonly token: string
  ) {}

  async get<T>(path: string): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!res.ok) {
      console.log('RES', res);
      throw new Error(`GET ${path} failed: ${res.status}`);
    }

    return res.json() as Promise<T>;
  }

  async post<T, B = unknown>(path: string, body: B): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      console.log('RES', res);
      throw new Error(`POST ${path} failed: ${res.status}`);
    }

    return res.json() as Promise<T>;
  }

  async put<T = void, B = unknown>(path: string, body: B): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      console.log('RES', res);
      throw new Error(`PUT ${path} failed: ${res.status}`);
    }

    const contentLength = res.headers.get('content-length');
    if (res.status === 204 || contentLength === '0') {
      return undefined as T;
    }

    const contentType = res.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      return undefined as T;
    }

    return res.json() as Promise<T>;
  }

  async delete<T = void>(path: string): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${this.token}`,
        'Content-Type': 'application/json'
      }
    });

    if (!res.ok) {
      throw new Error(`DELETE ${path} failed: ${res.status}`);
    }

    try {
      return (await res.json()) as T;
    } catch {
      return undefined as T;
    }
  }
}
