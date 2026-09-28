import { readFileSync } from 'node:fs'
const config=JSON.parse(readFileSync(new URL('../dist/build-config.json',import.meta.url),'utf8'))
const target=new URL(config.api_base_url)
if(target.protocol!=='https:'||['localhost','127.0.0.1','[::1]'].includes(target.hostname))throw new Error('Public deployment requires a real HTTPS FastAPI URL. Rebuild for the target environment.')
console.log('Deployment target configuration accepted:',target.origin)
