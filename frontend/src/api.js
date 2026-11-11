export class ApiError extends Error {
    code;
    details;
    status;
    constructor(body, status) {
        super(body.message);
        this.name = 'ApiError';
        this.code = body.code;
        this.details = body.details;
        this.status = status;
    }
}
async function request(method, path, body) {
    const isForm = body instanceof FormData;
    const response = await fetch(path, {
        method,
        headers: body === undefined || isForm
            ? undefined
            : { 'Content-Type': 'application/json' },
        body: body === undefined
            ? undefined
            : isForm
                ? body
                : JSON.stringify(body),
    });
    if (!response.ok) {
        let errorBody = {};
        try {
            errorBody = (await response.json());
        }
        catch {
            errorBody = {};
        }
        throw new ApiError({
            code: errorBody.code ?? 'request_failed',
            message: errorBody.message ?? `Request failed (${response.status}).`,
            details: errorBody.details ?? {},
        }, response.status);
    }
    return (await response.json());
}
export const getModels = () => request('GET', '/api/models');
export const getSamples = () => request('GET', '/api/samples');
export const uploadFile = (file) => {
    const body = new FormData();
    body.append('file', file);
    return request('POST', '/api/uploads', body);
};
export const uploadSample = (sample) => {
    const body = new FormData();
    body.append('sample', sample);
    return request('POST', '/api/uploads', body);
};
export const createSplit = (uploadId, body) => request('POST', `/api/uploads/${encodeURIComponent(uploadId)}/split`, body);
export const preflight = (uploadId, body) => request('POST', `/api/uploads/${encodeURIComponent(uploadId)}/preflight`, body);
export const startRun = (body) => request('POST', '/api/runs', body);
export const getRun = (runId) => request('GET', `/api/runs/${encodeURIComponent(runId)}`);
export const getSummary = (runId) => request('GET', `/api/runs/${encodeURIComponent(runId)}/summary`);
export const getPairs = (runId) => request('GET', `/api/runs/${encodeURIComponent(runId)}/pairs`);
export const getDisagreements = (runId, params) => {
    const query = new URLSearchParams({
        a: params.a,
        b: params.b,
        bucket: params.bucket ?? 'all',
        page: String(params.page ?? 1),
        page_size: String(params.pageSize ?? 25),
    });
    if (params.trueClass)
        query.set('class', params.trueClass);
    return request('GET', `/api/runs/${encodeURIComponent(runId)}/disagreements?${query}`);
};
export const getSlices = (runId, params) => {
    const query = new URLSearchParams(params);
    return request('GET', `/api/runs/${encodeURIComponent(runId)}/slices?${query}`);
};
export const listRuns = () => request('GET', '/api/runs');
export const deleteRun = (runId) => request('DELETE', `/api/runs/${encodeURIComponent(runId)}`);
