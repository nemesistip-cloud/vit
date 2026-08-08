import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs'
import { resolve, relative, dirname, join } from 'node:path'

const dist = resolve(process.argv[2] ?? 'dist')
const indexPath = join(dist, 'index.html')

if (!existsSync(indexPath)) {
  throw new Error(`Frontend asset check failed: ${relative(process.cwd(), indexPath)} is missing`)
}

const missing = []
const checked = new Set()

function checkAsset(assetPath, source) {
  const cleanPath = assetPath.split(/[?#]/, 1)[0]
  if (!cleanPath || cleanPath.startsWith('http://') || cleanPath.startsWith('https://') || cleanPath.startsWith('//')) {
    return
  }

  const target = cleanPath.startsWith('/')
    ? join(dist, cleanPath.slice(1))
    : resolve(dirname(source), cleanPath)

  if (!existsSync(target) || !statSync(target).isFile()) {
    missing.push(`${relative(dist, source)} -> ${assetPath}`)
  }
  return target
}

const index = readFileSync(indexPath, 'utf8')
for (const match of index.matchAll(/(?:src|href)="([^"]+)"/g)) {
  checkAsset(match[1], indexPath)
}

const assetsDir = join(dist, 'assets')
for (const name of readdirSync(assetsDir)) {
  if (!name.endsWith('.js')) continue
  const source = join(assetsDir, name)
  if (checked.has(source)) continue
  checked.add(source)
  const code = readFileSync(source, 'utf8')
  for (const match of code.matchAll(/import\(["']([^"']+\.js)["']\)/g)) {
    checkAsset(match[1], source)
  }
}

const adminChunks = readdirSync(assetsDir).filter((name) => /^Admin-[^/]+\.js$/.test(name))
if (adminChunks.length === 0) {
  missing.push('frontend/dist/assets -> Admin-*.js')
}

if (missing.length > 0) {
  console.error('Frontend asset check failed:')
  for (const entry of missing) console.error(`- ${entry}`)
  process.exit(1)
}

console.log(`Frontend asset check passed: ${adminChunks.length} Admin chunk(s), all referenced assets exist.`)