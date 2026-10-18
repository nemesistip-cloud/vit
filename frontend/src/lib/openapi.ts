export interface OpenAPISpec {
  openapi: string
  info: {
    title: string
    version: string
    description?: string
    termsOfService?: string
    contact?: { name?: string; url?: string; email?: string }
    license?: { name?: string; url?: string }
  }
  servers?: Array<{ url: string; description?: string }>
  tags?: Array<{ name: string; description?: string }>
  paths: Record<string, Record<string, any>>
  components?: {
    schemas?: Record<string, any>
    securitySchemes?: Record<string, any>
  }
}

export interface ParsedParameter {
  name: string
  in: 'path' | 'query' | 'header' | 'cookie'
  required: boolean
  description?: string
  schema?: any
  example?: any
}

export interface ParsedEndpoint {
  id: string
  path: string
  method: 'get' | 'post' | 'put' | 'patch' | 'delete'
  summary: string
  description: string
  tag: string
  operationId: string
  deprecated: boolean
  security: Array<Record<string, string[]>>
  parameters: ParsedParameter[]
  requestBody?: {
    description?: string
    required?: boolean
    mediaType: string
    schema?: any
    example?: any
  }
  responses: Array<{
    statusCode: string
    description: string
    mediaType?: string
    schema?: any
    example?: any
  }>
}

export interface ParsedGroup {
  name: string
  description?: string
  endpoints: ParsedEndpoint[]
}

export interface OpenAPIMetrics {
  totalEndpoints: number
  methodCounts: {
    GET: number
    POST: number
    PUT: number
    PATCH: number
    DELETE: number
  }
  schemaCount: number
  securitySchemes: string[]
  version: string
}

/**
 * Resolves a $ref pointer like "#/components/schemas/User" inside an OpenAPI spec.
 */
export function resolveSchemaRef(ref: string, spec: OpenAPISpec): any {
  if (!ref || typeof ref !== 'string') return null
  if (ref.startsWith('#/components/schemas/')) {
    const schemaName = ref.replace('#/components/schemas/', '')
    return spec.components?.schemas?.[schemaName] || null
  }
  return null
}

/**
 * Generates mock JSON data based on an OpenAPI schema object.
 */
export function generateMockFromSchema(
  schema: any,
  spec?: OpenAPISpec,
  depth = 0
): any {
  if (!schema || depth > 5) return null

  // Handle $ref
  if (schema.$ref && spec) {
    const resolved = resolveSchemaRef(schema.$ref, spec)
    if (resolved) {
      return generateMockFromSchema(resolved, spec, depth + 1)
    }
    const name = schema.$ref.split('/').pop()
    return `{Ref: ${name}}`
  }

  if (schema.example !== undefined) return schema.example
  if (schema.default !== undefined) return schema.default

  // Handle allOf / anyOf / oneOf
  if (schema.allOf && Array.isArray(schema.allOf)) {
    let merged: Record<string, any> = {}
    for (const sub of schema.allOf) {
      const val = generateMockFromSchema(sub, spec, depth + 1)
      if (val && typeof val === 'object' && !Array.isArray(val)) {
        merged = { ...merged, ...val }
      }
    }
    return merged
  }

  if ((schema.anyOf || schema.oneOf) && Array.isArray(schema.anyOf || schema.oneOf)) {
    const list = schema.anyOf || schema.oneOf
    return generateMockFromSchema(list[0], spec, depth + 1)
  }

  const type = schema.type || (schema.properties ? 'object' : 'string')

  if (type === 'object' || schema.properties) {
    const props = schema.properties || {}
    const obj: Record<string, any> = {}
    for (const [key, propSchema] of Object.entries<any>(props)) {
      if (key.toLowerCase().includes('password') || key.toLowerCase().includes('secret')) {
        obj[key] = '••••••••'
      } else if (key.toLowerCase().includes('token') || key.toLowerCase().includes('key')) {
        obj[key] = 'vit_key_sample_12345'
      } else {
        obj[key] = generateMockFromSchema(propSchema, spec, depth + 1)
      }
    }
    return obj
  }

  if (type === 'array') {
    const itemSchema = schema.items || {}
    const sample = generateMockFromSchema(itemSchema, spec, depth + 1)
    return [sample]
  }

  if (schema.enum && Array.isArray(schema.enum) && schema.enum.length > 0) {
    return schema.enum[0]
  }

  if (type === 'integer' || type === 'number') {
    if (schema.minimum !== undefined) return schema.minimum
    return 100
  }

  if (type === 'boolean') {
    return true
  }

  // String formats
  if (schema.format === 'date-time') return new Date().toISOString()
  if (schema.format === 'uuid') return '123e4567-e89b-12d3-a456-426614174000'
  if (schema.format === 'email') return 'developer@vit.network'
  if (schema.format === 'uri' || schema.format === 'url') return 'https://vit.network'

  return schema.title || 'sample_text'
}

/**
 * Parses raw OpenAPI specification into structured endpoints and group metrics.
 */
export function parseOpenAPISpec(spec: OpenAPISpec): {
  endpoints: ParsedEndpoint[]
  groups: ParsedGroup[]
  metrics: OpenAPIMetrics
} {
  const endpoints: ParsedEndpoint[] = []
  const groupMap = new Map<string, ParsedEndpoint[]>()

  const validMethods: Array<'get' | 'post' | 'put' | 'patch' | 'delete'> = [
    'get',
    'post',
    'put',
    'patch',
    'delete',
  ]

  const methodCounts = {
    GET: 0,
    POST: 0,
    PUT: 0,
    PATCH: 0,
    DELETE: 0,
  }

  for (const [path, pathObj] of Object.entries(spec.paths || {})) {
    for (const method of validMethods) {
      if (!pathObj[method]) continue

      const op = pathObj[method]
      const uppercaseMethod = method.toUpperCase() as keyof typeof methodCounts
      methodCounts[uppercaseMethod]++

      const rawTags = op.tags && op.tags.length > 0 ? op.tags : ['General']
      const primaryTag = rawTags[0]

      // Parse parameters (path + operation level)
      const rawParams = [...(pathObj.parameters || []), ...(op.parameters || [])]
      const parameters: ParsedParameter[] = rawParams.map((p: any) => ({
        name: p.name,
        in: p.in || 'query',
        required: p.required ?? p.in === 'path',
        description: p.description || '',
        schema: p.schema,
        example: p.example,
      }))

      // Parse request body
      let requestBody: ParsedEndpoint['requestBody'] = undefined
      if (op.requestBody) {
        const content = op.requestBody.content || {}
        const mediaType = Object.keys(content)[0] || 'application/json'
        const mediaObj = content[mediaType] || {}
        requestBody = {
          description: op.requestBody.description,
          required: op.requestBody.required ?? false,
          mediaType,
          schema: mediaObj.schema,
          example: mediaObj.example || generateMockFromSchema(mediaObj.schema, spec),
        }
      }

      // Parse responses
      const responses: ParsedEndpoint['responses'] = []
      if (op.responses) {
        for (const [statusCode, respObj] of Object.entries<any>(op.responses)) {
          const content = respObj.content || {}
          const mediaType = Object.keys(content)[0]
          const mediaObj = mediaType ? content[mediaType] : undefined
          responses.push({
            statusCode,
            description: respObj.description || '',
            mediaType,
            schema: mediaObj?.schema,
            example: mediaObj?.example || (mediaObj?.schema ? generateMockFromSchema(mediaObj.schema, spec) : undefined),
          })
        }
      }

      const endpoint: ParsedEndpoint = {
        id: `${method}-${path}`,
        path,
        method,
        summary: op.summary || op.operationId || `${uppercaseMethod} ${path}`,
        description: op.description || '',
        tag: primaryTag,
        operationId: op.operationId || `${method}_${path.replace(/[^a-zA-Z0-9]/g, '_')}`,
        deprecated: op.deprecated ?? false,
        security: op.security || spec.components?.securitySchemes ? [{ apiKey: [] }] : [],
        parameters,
        requestBody,
        responses,
      }

      endpoints.push(endpoint)

      if (!groupMap.has(primaryTag)) {
        groupMap.set(primaryTag, [])
      }
      groupMap.get(primaryTag)!.push(endpoint)
    }
  }

  // Build groups list ordered by spec tags or alphabetically
  const specTagDescriptions = new Map<string, string>()
  if (spec.tags) {
    for (const t of spec.tags) {
      if (t.name) specTagDescriptions.set(t.name, t.description || '')
    }
  }

  const groups: ParsedGroup[] = Array.from(groupMap.entries()).map(([name, groupEndpoints]) => ({
    name,
    description: specTagDescriptions.get(name),
    endpoints: groupEndpoints.sort((a, b) => a.path.localeCompare(b.path)),
  })).sort((a, b) => a.name.localeCompare(b.name))

  const securitySchemes = Object.keys(spec.components?.securitySchemes || {})
  if (securitySchemes.length === 0) {
    securitySchemes.push('Bearer Auth', 'API Key (X-API-Key)')
  }

  const metrics: OpenAPIMetrics = {
    totalEndpoints: endpoints.length,
    methodCounts,
    schemaCount: Object.keys(spec.components?.schemas || {}).length,
    securitySchemes,
    version: spec.info?.version || '1.2.0',
  }

  return { endpoints, groups, metrics }
}

/**
 * Generate cURL, JavaScript fetch, and Python requests code snippets for an endpoint.
 */
export function generateCodeExamples(
  endpoint: ParsedEndpoint,
  baseUrl: string,
  paramValues: Record<string, string> = {},
  bodyValue?: string,
  headersValue: Record<string, string> = {}
): { curl: string; js: string; python: string } {
  let fullPath = endpoint.path

  // Substitute path parameters
  for (const param of endpoint.parameters.filter((p) => p.in === 'path')) {
    const val = paramValues[param.name] || `{${param.name}}`
    fullPath = fullPath.replace(`{${param.name}}`, val)
  }

  // Construct query parameters
  const queryParams = endpoint.parameters
    .filter((p) => p.in === 'query' && paramValues[p.name])
    .map((p) => `${encodeURIComponent(p.name)}=${encodeURIComponent(paramValues[p.name])}`)
    .join('&')

  const fullUrl = `${baseUrl.replace(/\/$/, '')}${fullPath}${queryParams ? `?${queryParams}` : ''}`
  const methodUpper = endpoint.method.toUpperCase()

  const combinedHeaders: Record<string, string> = {
    Accept: 'application/json',
    ...headersValue,
  }

  if (endpoint.requestBody) {
    combinedHeaders['Content-Type'] = endpoint.requestBody.mediaType || 'application/json'
  }

  // cURL
  const curlHeaders = Object.entries(combinedHeaders)
    .map(([k, v]) => `  -H "${k}: ${v}" \\`)
    .join('\n')

  let curlBody = ''
  if (['POST', 'PUT', 'PATCH'].includes(methodUpper) && bodyValue) {
    curlBody = `\n  -d '${bodyValue.replace(/'/g, "'\\''")}'`
  }

  const curl = `curl -X ${methodUpper} "${fullUrl}" \\\n${curlHeaders}${curlBody}`

  // JavaScript
  const jsHeaders = JSON.stringify(combinedHeaders, null, 2)
  let jsBody = ''
  if (['POST', 'PUT', 'PATCH'].includes(methodUpper) && bodyValue) {
    jsBody = `,\n  body: JSON.stringify(${bodyValue})`
  }

  const js = `const response = await fetch("${fullUrl}", {
  method: "${methodUpper}",
  headers: ${jsHeaders}${jsBody}
});
const data = await response.json();
console.log(data);`

  // Python
  const pyHeaders = JSON.stringify(combinedHeaders, null, 2)
  let pyBody = ''
  if (['POST', 'PUT', 'PATCH'].includes(methodUpper) && bodyValue) {
    pyBody = `, json=${bodyValue}`
  }

  const python = `import requests

url = "${fullUrl}"
headers = ${pyHeaders}

response = requests.${endpoint.method.toLowerCase()}(url, headers=headers${pyBody})
print(response.status_code)
print(response.json())`

  return { curl, js, python }
}
