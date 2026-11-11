export type ApiErrorBody = {
  code: string
  message: string
  details: Record<string, unknown>
}

export class ApiError extends Error {
  readonly code: string
  readonly details: Record<string, unknown>
  readonly status: number

  constructor(body: ApiErrorBody, status: number) {
    super(body.message)
    this.name = 'ApiError'
    this.code = body.code
    this.details = body.details
    this.status = status
  }
}

export type ProfileColumn = {
  name: string
  kind: string
  missing_pct: number
}

export type UploadResponse = {
  upload_id: string
  display_filename: string
  fingerprint: string
  size_bytes: number
  n_rows: number
  n_cols: number
  header: string[]
  profile: {
    n_rows: number
    n_cols: number
    columns: ProfileColumn[]
  }
}

export type ClassCounts = {
  n_before: number
  n_after: number
  n_train: number
  n_test: number
}

export type SplitResponse = {
  split_id: string
  n_labelled: number
  dropped_missing_target: number
  trimmed_labels: number
  n_train: number
  n_test: number
  class_table: Record<string, ClassCounts>
  warnings: string[]
}

export type FeatureFlag = {
  flag: string | null
  default_decision: 'include' | 'exclude' | 'undecided'
  reason: string
  details: Record<string, unknown>
}

export type PreflightResponse = {
  report: {
    sections: Array<{
      id: string
      source: string
      items: Array<{ kind: string; message: string; data: unknown }>
    }>
    warnings: string[]
    missing_tokens: { features: string[]; target: string[] }
  }
  flags: Record<string, FeatureFlag>
  undecided: string[]
  included: string[]
  excluded: string[]
  needs_independence_confirmation: boolean
}

export type ModelInfo = {
  key: string
  label: string
  baseline: boolean
  selectable: boolean
  supports_proba: boolean
}

export type RunStatus = {
  run_id: string
  state: string
  stage: string
  models: Record<
    string,
    { status: string; fit_seconds?: number; error?: string }
  >
  error: string | null
  config: {
    display_filename: string
    models: string[]
    created_at: string
  }
  quality: PreflightResponse['report'] | null
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const isForm = body instanceof FormData
  const response = await fetch(path, {
    method,
    headers:
      body === undefined || isForm
        ? undefined
        : { 'Content-Type': 'application/json' },
    body:
      body === undefined
        ? undefined
        : isForm
          ? body
          : JSON.stringify(body),
  })

  if (!response.ok) {
    let errorBody: Partial<ApiErrorBody> = {}
    try {
      errorBody = (await response.json()) as Partial<ApiErrorBody>
    } catch {
      errorBody = {}
    }
    throw new ApiError(
      {
        code: errorBody.code ?? 'request_failed',
        message: errorBody.message ?? `Request failed (${response.status}).`,
        details: errorBody.details ?? {},
      },
      response.status,
    )
  }

  return (await response.json()) as T
}

export const getModels = () =>
  request<{ models: ModelInfo[] }>('GET', '/api/models')

export const getSamples = () =>
  request<{ samples: Array<{ name: string; label: string }> }>(
    'GET',
    '/api/samples',
  )

export const uploadFile = (file: File) => {
  const body = new FormData()
  body.append('file', file)
  return request<UploadResponse>('POST', '/api/uploads', body)
}

export const uploadSample = (sample: string) => {
  const body = new FormData()
  body.append('sample', sample)
  return request<UploadResponse>('POST', '/api/uploads', body)
}

export const createSplit = (
  uploadId: string,
  body: {
    target: string
    target_missing_tokens: string[]
    seed: number
    test_size: number
  },
) =>
  request<SplitResponse>(
    'POST',
    `/api/uploads/${encodeURIComponent(uploadId)}/split`,
    body,
  )

export const preflight = (
  uploadId: string,
  body: {
    split_id: string
    missing_tokens: string[]
    column_decisions: Record<string, string>
  },
) =>
  request<PreflightResponse>(
    'POST',
    `/api/uploads/${encodeURIComponent(uploadId)}/preflight`,
    body,
  )

export const startRun = (body: {
  upload_id: string
  split_id: string
  missing_tokens: string[]
  column_decisions: Record<string, string>
  models: string[]
  class_weight: boolean
  independence_confirmed: boolean
}) => request<{ run_id: string; state: string }>('POST', '/api/runs', body)

export const getRun = (runId: string) =>
  request<RunStatus>('GET', `/api/runs/${encodeURIComponent(runId)}`)

export const getSummary = (runId: string) =>
  request<unknown>('GET', `/api/runs/${encodeURIComponent(runId)}/summary`)

export const getPairs = (runId: string) =>
  request<unknown>('GET', `/api/runs/${encodeURIComponent(runId)}/pairs`)

export const getDisagreements = (
  runId: string,
  params: { a: string; b: string; bucket?: string; trueClass?: string; page?: number; pageSize?: number },
) => {
  const query = new URLSearchParams({
    a: params.a,
    b: params.b,
    bucket: params.bucket ?? 'all',
    page: String(params.page ?? 1),
    page_size: String(params.pageSize ?? 25),
  })
  if (params.trueClass) query.set('class', params.trueClass)
  return request<unknown>(
    'GET',
    `/api/runs/${encodeURIComponent(runId)}/disagreements?${query}`,
  )
}

export const getSlices = (
  runId: string,
  params: { a: string; b: string; feature: string },
) => {
  const query = new URLSearchParams(params)
  return request<unknown>(
    'GET',
    `/api/runs/${encodeURIComponent(runId)}/slices?${query}`,
  )
}

export const listRuns = () => request<unknown>('GET', '/api/runs')

export const deleteRun = (runId: string) =>
  request<{ deleted: boolean }>(
    'DELETE',
    `/api/runs/${encodeURIComponent(runId)}`,
  )
