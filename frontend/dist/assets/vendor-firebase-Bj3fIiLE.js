/**
 * @license
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Ns=()=>{};var Fi={};/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Ir=function(r){const e=[];let n=0;for(let o=0;o<r.length;o++){let a=r.charCodeAt(o);a<128?e[n++]=a:a<2048?(e[n++]=a>>6|192,e[n++]=a&63|128):(a&64512)===55296&&o+1<r.length&&(r.charCodeAt(o+1)&64512)===56320?(a=65536+((a&1023)<<10)+(r.charCodeAt(++o)&1023),e[n++]=a>>18|240,e[n++]=a>>12&63|128,e[n++]=a>>6&63|128,e[n++]=a&63|128):(e[n++]=a>>12|224,e[n++]=a>>6&63|128,e[n++]=a&63|128)}return e},Rs=function(r){const e=[];let n=0,o=0;for(;n<r.length;){const a=r[n++];if(a<128)e[o++]=String.fromCharCode(a);else if(a>191&&a<224){const d=r[n++];e[o++]=String.fromCharCode((a&31)<<6|d&63)}else if(a>239&&a<365){const d=r[n++],f=r[n++],v=r[n++],I=((a&7)<<18|(d&63)<<12|(f&63)<<6|v&63)-65536;e[o++]=String.fromCharCode(55296+(I>>10)),e[o++]=String.fromCharCode(56320+(I&1023))}else{const d=r[n++],f=r[n++];e[o++]=String.fromCharCode((a&15)<<12|(d&63)<<6|f&63)}}return e.join("")},Er={byteToCharMap_:null,charToByteMap_:null,byteToCharMapWebSafe_:null,charToByteMapWebSafe_:null,ENCODED_VALS_BASE:"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",get ENCODED_VALS(){return this.ENCODED_VALS_BASE+"+/="},get ENCODED_VALS_WEBSAFE(){return this.ENCODED_VALS_BASE+"-_."},HAS_NATIVE_SUPPORT:typeof atob=="function",encodeByteArray(r,e){if(!Array.isArray(r))throw Error("encodeByteArray takes an array as a parameter");this.init_();const n=e?this.byteToCharMapWebSafe_:this.byteToCharMap_,o=[];for(let a=0;a<r.length;a+=3){const d=r[a],f=a+1<r.length,v=f?r[a+1]:0,I=a+2<r.length,A=I?r[a+2]:0,D=d>>2,T=(d&3)<<4|v>>4;let B=(v&15)<<2|A>>6,W=A&63;I||(W=64,f||(B=64)),o.push(n[D],n[T],n[B],n[W])}return o.join("")},encodeString(r,e){return this.HAS_NATIVE_SUPPORT&&!e?btoa(r):this.encodeByteArray(Ir(r),e)},decodeString(r,e){return this.HAS_NATIVE_SUPPORT&&!e?atob(r):Rs(this.decodeStringToByteArray(r,e))},decodeStringToByteArray(r,e){this.init_();const n=e?this.charToByteMapWebSafe_:this.charToByteMap_,o=[];for(let a=0;a<r.length;){const d=n[r.charAt(a++)],v=a<r.length?n[r.charAt(a)]:0;++a;const A=a<r.length?n[r.charAt(a)]:64;++a;const T=a<r.length?n[r.charAt(a)]:64;if(++a,d==null||v==null||A==null||T==null)throw new Ds;const B=d<<2|v>>4;if(o.push(B),A!==64){const W=v<<4&240|A>>2;if(o.push(W),T!==64){const V=A<<6&192|T;o.push(V)}}}return o},init_(){if(!this.byteToCharMap_){this.byteToCharMap_={},this.charToByteMap_={},this.byteToCharMapWebSafe_={},this.charToByteMapWebSafe_={};for(let r=0;r<this.ENCODED_VALS.length;r++)this.byteToCharMap_[r]=this.ENCODED_VALS.charAt(r),this.charToByteMap_[this.byteToCharMap_[r]]=r,this.byteToCharMapWebSafe_[r]=this.ENCODED_VALS_WEBSAFE.charAt(r),this.charToByteMapWebSafe_[this.byteToCharMapWebSafe_[r]]=r,r>=this.ENCODED_VALS_BASE.length&&(this.charToByteMap_[this.ENCODED_VALS_WEBSAFE.charAt(r)]=r,this.charToByteMapWebSafe_[this.ENCODED_VALS.charAt(r)]=r)}}};class Ds extends Error{constructor(){super(...arguments),this.name="DecodeBase64StringError"}}const ks=function(r){const e=Ir(r);return Er.encodeByteArray(e,!0)},Ar=function(r){return ks(r).replace(/\./g,"")},Tr=function(r){try{return Er.decodeString(r,!0)}catch(e){console.error("base64Decode failed: ",e)}return null};/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function Os(){if(typeof self<"u")return self;if(typeof window<"u")return window;if(typeof global<"u")return global;throw new Error("Unable to locate global object.")}/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Ls=()=>Os().__FIREBASE_DEFAULTS__,Ms=()=>{if(typeof process>"u"||typeof Fi>"u")return;const r=Fi.__FIREBASE_DEFAULTS__;if(r)return JSON.parse(r)},Us=()=>{if(typeof document>"u")return;let r;try{r=document.cookie.match(/__FIREBASE_DEFAULTS__=([^;]+)/)}catch{return}const e=r&&Tr(r[1]);return e&&JSON.parse(e)},xs=()=>{try{return Ns()||Ls()||Ms()||Us()}catch(r){console.info(`Unable to get __FIREBASE_DEFAULTS__ due to: ${r}`);return}},Vs=r=>{var e;return(e=xs())==null?void 0:e[`_${r}`]};/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function st(){return typeof navigator<"u"&&typeof navigator.userAgent=="string"?navigator.userAgent:""}function Fs(){return typeof window<"u"&&!!(window.cordova||window.phonegap||window.PhoneGap)&&/ios|iphone|ipod|ipad|android|blackberry|iemobile/i.test(st())}function js(){return typeof navigator<"u"&&navigator.userAgent==="Cloudflare-Workers"}function Bs(){const r=typeof chrome=="object"?chrome.runtime:typeof browser=="object"?browser.runtime:void 0;return typeof r=="object"&&r.id!==void 0}function Hs(){return typeof navigator=="object"&&navigator.product==="ReactNative"}function $s(){try{return typeof indexedDB=="object"}catch{return!1}}function Gs(){return new Promise((r,e)=>{try{let n=!0;const o="validate-browser-context-for-indexeddb-analytics-module",a=self.indexedDB.open(o);a.onsuccess=()=>{a.result.close(),n||self.indexedDB.deleteDatabase(o),r(!0)},a.onupgradeneeded=()=>{n=!1},a.onerror=()=>{var d;e(((d=a.error)==null?void 0:d.message)||"")}}catch(n){e(n)}})}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Ws="FirebaseError";class It extends Error{constructor(e,n,o){super(n),this.code=e,this.customData=o,this.name=Ws,Object.setPrototypeOf(this,It.prototype),Error.captureStackTrace&&Error.captureStackTrace(this,fe.prototype.create)}}class fe{constructor(e,n,o){this.service=e,this.serviceName=n,this.errors=o}create(e,...n){const o=n[0]||{},a=`${this.service}/${e}`,d=this.errors[e],f=d?zs(d,o):"Error",v=`${this.serviceName}: ${f} (${a}).`;return new It(a,v,o)}}function zs(r,e){return r.replace(qs,(n,o)=>{const a=e[o];return a!=null?String(a):`<${o}?>`})}const qs=/\{\$([^}]+)}/g;/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function Sr(r){const e=[];for(const[n,o]of Object.entries(r))Array.isArray(o)?o.forEach(a=>{e.push(encodeURIComponent(n)+"="+encodeURIComponent(a))}):e.push(encodeURIComponent(n)+"="+encodeURIComponent(o));return e.length?"&"+e.join("&"):""}function Ks(r,e){const n=new Js(r,e);return n.subscribe.bind(n)}class Js{constructor(e,n){this.observers=[],this.unsubscribes=[],this.observerCount=0,this.task=Promise.resolve(),this.finalized=!1,this.onNoObservers=n,this.task.then(()=>{e(this)}).catch(o=>{this.error(o)})}next(e){this.forEachObserver(n=>{n.next(e)})}error(e){this.forEachObserver(n=>{n.error(e)}),this.close(e)}complete(){this.forEachObserver(e=>{e.complete()}),this.close()}subscribe(e,n,o){let a;if(e===void 0&&n===void 0&&o===void 0)throw new Error("Missing Observer.");Xs(e,["next","error","complete"])?a=e:a={next:e,error:n,complete:o},a.next===void 0&&(a.next=yn),a.error===void 0&&(a.error=yn),a.complete===void 0&&(a.complete=yn);const d=this.unsubscribeOne.bind(this,this.observers.length);return this.finalized&&this.task.then(()=>{try{this.finalError?a.error(this.finalError):a.complete()}catch{}}),this.observers.push(a),d}unsubscribeOne(e){this.observers===void 0||this.observers[e]===void 0||(delete this.observers[e],this.observerCount-=1,this.observerCount===0&&this.onNoObservers!==void 0&&this.onNoObservers(this))}forEachObserver(e){if(!this.finalized)for(let n=0;n<this.observers.length;n++)this.sendOne(n,e)}sendOne(e,n){this.task.then(()=>{if(this.observers!==void 0&&this.observers[e]!==void 0)try{n(this.observers[e])}catch(o){typeof console<"u"&&console.error&&console.error(o)}})}close(e){this.finalized||(this.finalized=!0,e!==void 0&&(this.finalError=e),this.task.then(()=>{this.observers=void 0,this.onNoObservers=void 0}))}}function Xs(r,e){if(typeof r!="object"||r===null)return!1;for(const n of e)if(n in r&&typeof r[n]=="function")return!0;return!1}function yn(){}/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function de(r){return r&&r._delegate?r._delegate:r}/**
 * @license
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function br(r){try{return(r.startsWith("http://")||r.startsWith("https://")?new URL(r).hostname:r).endsWith(".cloudworkstations.dev")}catch{return!1}}class Ht{constructor(e,n,o){this.name=e,this.instanceFactory=n,this.type=o,this.multipleInstances=!1,this.serviceProps={},this.instantiationMode="LAZY",this.onInstanceCreated=null}setInstantiationMode(e){return this.instantiationMode=e,this}setMultipleInstances(e){return this.multipleInstances=e,this}setServiceProps(e){return this.serviceProps=e,this}setInstanceCreatedCallback(e){return this.onInstanceCreated=e,this}}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var R;(function(r){r[r.DEBUG=0]="DEBUG",r[r.VERBOSE=1]="VERBOSE",r[r.INFO=2]="INFO",r[r.WARN=3]="WARN",r[r.ERROR=4]="ERROR",r[r.SILENT=5]="SILENT"})(R||(R={}));const Ys={debug:R.DEBUG,verbose:R.VERBOSE,info:R.INFO,warn:R.WARN,error:R.ERROR,silent:R.SILENT},Qs=R.INFO,Zs={[R.DEBUG]:"log",[R.VERBOSE]:"log",[R.INFO]:"info",[R.WARN]:"warn",[R.ERROR]:"error"},to=(r,e,...n)=>{if(e<r.logLevel)return;const o=new Date().toISOString(),a=Zs[e];if(a)console[a](`[${o}]  ${r.name}:`,...n);else throw new Error(`Attempted to log a message with an invalid logType (value: ${e})`)};class kn{constructor(e){this.name=e,this._logLevel=Qs,this._logHandler=to,this._userLogHandler=null}get logLevel(){return this._logLevel}set logLevel(e){if(!(e in R))throw new TypeError(`Invalid value "${e}" assigned to \`logLevel\``);this._logLevel=e}setLogLevel(e){this._logLevel=typeof e=="string"?Ys[e]:e}get logHandler(){return this._logHandler}set logHandler(e){if(typeof e!="function")throw new TypeError("Value assigned to `logHandler` must be a function");this._logHandler=e}get userLogHandler(){return this._userLogHandler}set userLogHandler(e){this._userLogHandler=e}debug(...e){this._userLogHandler&&this._userLogHandler(this,R.DEBUG,...e),this._logHandler(this,R.DEBUG,...e)}log(...e){this._userLogHandler&&this._userLogHandler(this,R.VERBOSE,...e),this._logHandler(this,R.VERBOSE,...e)}info(...e){this._userLogHandler&&this._userLogHandler(this,R.INFO,...e),this._logHandler(this,R.INFO,...e)}warn(...e){this._userLogHandler&&this._userLogHandler(this,R.WARN,...e),this._logHandler(this,R.WARN,...e)}error(...e){this._userLogHandler&&this._userLogHandler(this,R.ERROR,...e),this._logHandler(this,R.ERROR,...e)}}const eo=(r,e)=>e.some(n=>r instanceof n);let ji,Bi;function no(){return ji||(ji=[IDBDatabase,IDBObjectStore,IDBIndex,IDBCursor,IDBTransaction])}function io(){return Bi||(Bi=[IDBCursor.prototype.advance,IDBCursor.prototype.continue,IDBCursor.prototype.continuePrimaryKey])}const Cr=new WeakMap,bn=new WeakMap,Pr=new WeakMap,_n=new WeakMap,On=new WeakMap;function ro(r){const e=new Promise((n,o)=>{const a=()=>{r.removeEventListener("success",d),r.removeEventListener("error",f)},d=()=>{n(_t(r.result)),a()},f=()=>{o(r.error),a()};r.addEventListener("success",d),r.addEventListener("error",f)});return e.then(n=>{n instanceof IDBCursor&&Cr.set(n,r)}).catch(()=>{}),On.set(e,r),e}function so(r){if(bn.has(r))return;const e=new Promise((n,o)=>{const a=()=>{r.removeEventListener("complete",d),r.removeEventListener("error",f),r.removeEventListener("abort",f)},d=()=>{n(),a()},f=()=>{o(r.error||new DOMException("AbortError","AbortError")),a()};r.addEventListener("complete",d),r.addEventListener("error",f),r.addEventListener("abort",f)});bn.set(r,e)}let Cn={get(r,e,n){if(r instanceof IDBTransaction){if(e==="done")return bn.get(r);if(e==="objectStoreNames")return r.objectStoreNames||Pr.get(r);if(e==="store")return n.objectStoreNames[1]?void 0:n.objectStore(n.objectStoreNames[0])}return _t(r[e])},set(r,e,n){return r[e]=n,!0},has(r,e){return r instanceof IDBTransaction&&(e==="done"||e==="store")?!0:e in r}};function oo(r){Cn=r(Cn)}function ao(r){return r===IDBDatabase.prototype.transaction&&!("objectStoreNames"in IDBTransaction.prototype)?function(e,...n){const o=r.call(wn(this),e,...n);return Pr.set(o,e.sort?e.sort():[e]),_t(o)}:io().includes(r)?function(...e){return r.apply(wn(this),e),_t(Cr.get(this))}:function(...e){return _t(r.apply(wn(this),e))}}function ho(r){return typeof r=="function"?ao(r):(r instanceof IDBTransaction&&so(r),eo(r,no())?new Proxy(r,Cn):r)}function _t(r){if(r instanceof IDBRequest)return ro(r);if(_n.has(r))return _n.get(r);const e=ho(r);return e!==r&&(_n.set(r,e),On.set(e,r)),e}const wn=r=>On.get(r);function co(r,e,{blocked:n,upgrade:o,blocking:a,terminated:d}={}){const f=indexedDB.open(r,e),v=_t(f);return o&&f.addEventListener("upgradeneeded",I=>{o(_t(f.result),I.oldVersion,I.newVersion,_t(f.transaction),I)}),n&&f.addEventListener("blocked",I=>n(I.oldVersion,I.newVersion,I)),v.then(I=>{d&&I.addEventListener("close",()=>d()),a&&I.addEventListener("versionchange",A=>a(A.oldVersion,A.newVersion,A))}).catch(()=>{}),v}const lo=["get","getKey","getAll","getAllKeys","count"],uo=["put","add","delete","clear"],vn=new Map;function Hi(r,e){if(!(r instanceof IDBDatabase&&!(e in r)&&typeof e=="string"))return;if(vn.get(e))return vn.get(e);const n=e.replace(/FromIndex$/,""),o=e!==n,a=uo.includes(n);if(!(n in(o?IDBIndex:IDBObjectStore).prototype)||!(a||lo.includes(n)))return;const d=async function(f,...v){const I=this.transaction(f,a?"readwrite":"readonly");let A=I.store;return o&&(A=A.index(v.shift())),(await Promise.all([A[n](...v),a&&I.done]))[0]};return vn.set(e,d),d}oo(r=>({...r,get:(e,n,o)=>Hi(e,n)||r.get(e,n,o),has:(e,n)=>!!Hi(e,n)||r.has(e,n)}));/**
 * @license
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class fo{constructor(e){this.container=e}getPlatformInfoString(){return this.container.getProviders().map(n=>{if(po(n)){const o=n.getImmediate();return`${o.library}/${o.version}`}else return null}).filter(n=>n).join(" ")}}function po(r){const e=r.getComponent();return(e==null?void 0:e.type)==="VERSION"}const Pn="@firebase/app",$i="0.14.12";/**
 * @license
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const at=new kn("@firebase/app"),go="@firebase/app-compat",mo="@firebase/analytics-compat",yo="@firebase/analytics",_o="@firebase/app-check-compat",wo="@firebase/app-check",vo="@firebase/auth",Io="@firebase/auth-compat",Eo="@firebase/database",Ao="@firebase/data-connect",To="@firebase/database-compat",So="@firebase/functions",bo="@firebase/functions-compat",Co="@firebase/installations",Po="@firebase/installations-compat",No="@firebase/messaging",Ro="@firebase/messaging-compat",Do="@firebase/performance",ko="@firebase/performance-compat",Oo="@firebase/remote-config",Lo="@firebase/remote-config-compat",Mo="@firebase/storage",Uo="@firebase/storage-compat",xo="@firebase/firestore",Vo="@firebase/ai",Fo="@firebase/firestore-compat",jo="firebase",Bo="12.13.0",Ho={[Pn]:"fire-core",[go]:"fire-core-compat",[yo]:"fire-analytics",[mo]:"fire-analytics-compat",[wo]:"fire-app-check",[_o]:"fire-app-check-compat",[vo]:"fire-auth",[Io]:"fire-auth-compat",[Eo]:"fire-rtdb",[Ao]:"fire-data-connect",[To]:"fire-rtdb-compat",[So]:"fire-fn",[bo]:"fire-fn-compat",[Co]:"fire-iid",[Po]:"fire-iid-compat",[No]:"fire-fcm",[Ro]:"fire-fcm-compat",[Do]:"fire-perf",[ko]:"fire-perf-compat",[Oo]:"fire-rc",[Lo]:"fire-rc-compat",[Mo]:"fire-gcs",[Uo]:"fire-gcs-compat",[xo]:"fire-fst",[Fo]:"fire-fst-compat",[Vo]:"fire-vertex","fire-js":"fire-js",[jo]:"fire-js-all"};/**
 * @license
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const $o=new Map,Go=new Map,Gi=new Map;function Wi(r,e){try{r.container.addComponent(e)}catch(n){at.debug(`Component ${e.name} failed to register with FirebaseApp ${r.name}`,n)}}function $t(r){const e=r.name;if(Gi.has(e))return at.debug(`There were multiple attempts to register component ${e}.`),!1;Gi.set(e,r);for(const n of $o.values())Wi(n,r);for(const n of Go.values())Wi(n,r);return!0}function Ct(r){return r==null?!1:r.settings!==void 0}/**
 * @license
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Wo={"no-app":"No Firebase App '{$appName}' has been created - call initializeApp() first","bad-app-name":"Illegal App name: '{$appName}'","duplicate-app":"Firebase App named '{$appName}' already exists with different options or config","app-deleted":"Firebase App named '{$appName}' already deleted","server-app-deleted":"Firebase Server App has been deleted","no-options":"Need to provide options, when not being deployed to hosting via source.","invalid-app-argument":"firebase.{$appName}() takes either no argument or a Firebase App instance.","invalid-log-argument":"First argument to `onLog` must be null or a function.","idb-open":"Error thrown when opening IndexedDB. Original error: {$originalErrorMessage}.","idb-get":"Error thrown when reading from IndexedDB. Original error: {$originalErrorMessage}.","idb-set":"Error thrown when writing to IndexedDB. Original error: {$originalErrorMessage}.","idb-delete":"Error thrown when deleting from IndexedDB. Original error: {$originalErrorMessage}.","finalization-registry-not-supported":"FirebaseServerApp deleteOnDeref field defined but the JS runtime does not support FinalizationRegistry.","invalid-server-app-environment":"FirebaseServerApp is not for use in browser environments."},Ln=new fe("app","Firebase",Wo);/**
 * @license
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Be=Bo;function wt(r,e,n){let o=Ho[r]??r;n&&(o+=`-${n}`);const a=o.match(/\s|\//),d=e.match(/\s|\//);if(a||d){const f=[`Unable to register library "${o}" with version "${e}":`];a&&f.push(`library name "${o}" contains illegal characters (whitespace or "/")`),a&&d&&f.push("and"),d&&f.push(`version name "${e}" contains illegal characters (whitespace or "/")`),at.warn(f.join(" "));return}$t(new Ht(`${o}-version`,()=>({library:o,version:e}),"VERSION"))}/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const zo="firebase-heartbeat-database",qo=1,ue="firebase-heartbeat-store";let In=null;function Nr(){return In||(In=co(zo,qo,{upgrade:(r,e)=>{switch(e){case 0:try{r.createObjectStore(ue)}catch(n){console.warn(n)}}}}).catch(r=>{throw Ln.create("idb-open",{originalErrorMessage:r.message})})),In}async function Ko(r){try{const n=(await Nr()).transaction(ue),o=await n.objectStore(ue).get(Rr(r));return await n.done,o}catch(e){if(e instanceof It)at.warn(e.message);else{const n=Ln.create("idb-get",{originalErrorMessage:e==null?void 0:e.message});at.warn(n.message)}}}async function zi(r,e){try{const o=(await Nr()).transaction(ue,"readwrite");await o.objectStore(ue).put(e,Rr(r)),await o.done}catch(n){if(n instanceof It)at.warn(n.message);else{const o=Ln.create("idb-set",{originalErrorMessage:n==null?void 0:n.message});at.warn(o.message)}}}function Rr(r){return`${r.name}!${r.options.appId}`}/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Jo=1024,Xo=30;class Yo{constructor(e){this.container=e,this._heartbeatsCache=null;const n=this.container.getProvider("app").getImmediate();this._storage=new Zo(n),this._heartbeatsCachePromise=this._storage.read().then(o=>(this._heartbeatsCache=o,o))}async triggerHeartbeat(){var e,n;try{const a=this.container.getProvider("platform-logger").getImmediate().getPlatformInfoString(),d=qi();if(((e=this._heartbeatsCache)==null?void 0:e.heartbeats)==null&&(this._heartbeatsCache=await this._heartbeatsCachePromise,((n=this._heartbeatsCache)==null?void 0:n.heartbeats)==null)||this._heartbeatsCache.lastSentHeartbeatDate===d||this._heartbeatsCache.heartbeats.some(f=>f.date===d))return;if(this._heartbeatsCache.heartbeats.push({date:d,agent:a}),this._heartbeatsCache.heartbeats.length>Xo){const f=ta(this._heartbeatsCache.heartbeats);this._heartbeatsCache.heartbeats.splice(f,1)}return this._storage.overwrite(this._heartbeatsCache)}catch(o){at.warn(o)}}async getHeartbeatsHeader(){var e;try{if(this._heartbeatsCache===null&&await this._heartbeatsCachePromise,((e=this._heartbeatsCache)==null?void 0:e.heartbeats)==null||this._heartbeatsCache.heartbeats.length===0)return"";const n=qi(),{heartbeatsToSend:o,unsentEntries:a}=Qo(this._heartbeatsCache.heartbeats),d=Ar(JSON.stringify({version:2,heartbeats:o}));return this._heartbeatsCache.lastSentHeartbeatDate=n,a.length>0?(this._heartbeatsCache.heartbeats=a,await this._storage.overwrite(this._heartbeatsCache)):(this._heartbeatsCache.heartbeats=[],this._storage.overwrite(this._heartbeatsCache)),d}catch(n){return at.warn(n),""}}}function qi(){return new Date().toISOString().substring(0,10)}function Qo(r,e=Jo){const n=[];let o=r.slice();for(const a of r){const d=n.find(f=>f.agent===a.agent);if(d){if(d.dates.push(a.date),Ki(n)>e){d.dates.pop();break}}else if(n.push({agent:a.agent,dates:[a.date]}),Ki(n)>e){n.pop();break}o=o.slice(1)}return{heartbeatsToSend:n,unsentEntries:o}}class Zo{constructor(e){this.app=e,this._canUseIndexedDBPromise=this.runIndexedDBEnvironmentCheck()}async runIndexedDBEnvironmentCheck(){return $s()?Gs().then(()=>!0).catch(()=>!1):!1}async read(){if(await this._canUseIndexedDBPromise){const n=await Ko(this.app);return n!=null&&n.heartbeats?n:{heartbeats:[]}}else return{heartbeats:[]}}async overwrite(e){if(await this._canUseIndexedDBPromise){const o=await this.read();return zi(this.app,{lastSentHeartbeatDate:e.lastSentHeartbeatDate??o.lastSentHeartbeatDate,heartbeats:e.heartbeats})}else return}async add(e){if(await this._canUseIndexedDBPromise){const o=await this.read();return zi(this.app,{lastSentHeartbeatDate:e.lastSentHeartbeatDate??o.lastSentHeartbeatDate,heartbeats:[...o.heartbeats,...e.heartbeats]})}else return}}function Ki(r){return Ar(JSON.stringify({version:2,heartbeats:r})).length}function ta(r){if(r.length===0)return-1;let e=0,n=r[0].date;for(let o=1;o<r.length;o++)r[o].date<n&&(n=r[o].date,e=o);return e}/**
 * @license
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function ea(r){$t(new Ht("platform-logger",e=>new fo(e),"PRIVATE")),$t(new Ht("heartbeat",e=>new Yo(e),"PRIVATE")),wt(Pn,$i,r),wt(Pn,$i,"esm2020"),wt("fire-js","")}ea("");var na="firebase",ia="12.13.0";/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */wt(na,ia,"app");function Dr(){return{"dependent-sdk-initialized-before-auth":"Another Firebase SDK was initialized and is trying to use Auth before Auth is initialized. Please be sure to call `initializeAuth` or `getAuth` before starting any other Firebase SDK."}}const ra=Dr,kr=new fe("auth","Firebase",Dr());/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Le=new kn("@firebase/auth");function sa(r,...e){Le.logLevel<=R.WARN&&Le.warn(`Auth (${Be}): ${r}`,...e)}function De(r,...e){Le.logLevel<=R.ERROR&&Le.error(`Auth (${Be}): ${r}`,...e)}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function Ji(r,...e){throw Mn(r,...e)}function Or(r,...e){return Mn(r,...e)}function Lr(r,e,n){const o={...ra(),[e]:n};return new fe("auth","Firebase",o).create(e,{appName:r.name})}function ke(r){return Lr(r,"operation-not-supported-in-this-environment","Operations that alter the current user are not supported in conjunction with FirebaseServerApp")}function Mn(r,...e){if(typeof r!="string"){const n=e[0],o=[...e.slice(1)];return o[0]&&(o[0].appName=r.name),r._errorFactory.create(n,...o)}return kr.create(r,...e)}function C(r,e,...n){if(!r)throw Mn(e,...n)}function oe(r){const e="INTERNAL ASSERTION FAILED: "+r;throw De(e),new Error(e)}function Me(r,e){r||oe(e)}function oa(){return Xi()==="http:"||Xi()==="https:"}function Xi(){var r;return typeof self<"u"&&((r=self.location)==null?void 0:r.protocol)||null}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function aa(){return typeof navigator<"u"&&navigator&&"onLine"in navigator&&typeof navigator.onLine=="boolean"&&(oa()||Bs()||"connection"in navigator)?navigator.onLine:!0}function ha(){if(typeof navigator>"u")return null;const r=navigator;return r.languages&&r.languages[0]||r.language||null}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class pe{constructor(e,n){this.shortDelay=e,this.longDelay=n,Me(n>e,"Short delay should be less than long delay!"),this.isMobile=Fs()||Hs()}get(){return aa()?this.isMobile?this.longDelay:this.shortDelay:Math.min(5e3,this.shortDelay)}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function ca(r,e){Me(r.emulator,"Emulator should always be set here");const{url:n}=r.emulator;return e?`${n}${e.startsWith("/")?e.slice(1):e}`:n}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Mr{static initialize(e,n,o){this.fetchImpl=e,n&&(this.headersImpl=n),o&&(this.responseImpl=o)}static fetch(){if(this.fetchImpl)return this.fetchImpl;if(typeof self<"u"&&"fetch"in self)return self.fetch;if(typeof globalThis<"u"&&globalThis.fetch)return globalThis.fetch;if(typeof fetch<"u")return fetch;oe("Could not find fetch implementation, make sure you call FetchProvider.initialize() with an appropriate polyfill")}static headers(){if(this.headersImpl)return this.headersImpl;if(typeof self<"u"&&"Headers"in self)return self.Headers;if(typeof globalThis<"u"&&globalThis.Headers)return globalThis.Headers;if(typeof Headers<"u")return Headers;oe("Could not find Headers implementation, make sure you call FetchProvider.initialize() with an appropriate polyfill")}static response(){if(this.responseImpl)return this.responseImpl;if(typeof self<"u"&&"Response"in self)return self.Response;if(typeof globalThis<"u"&&globalThis.Response)return globalThis.Response;if(typeof Response<"u")return Response;oe("Could not find Response implementation, make sure you call FetchProvider.initialize() with an appropriate polyfill")}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const la={CREDENTIAL_MISMATCH:"custom-token-mismatch",MISSING_CUSTOM_TOKEN:"internal-error",INVALID_IDENTIFIER:"invalid-email",MISSING_CONTINUE_URI:"internal-error",INVALID_PASSWORD:"wrong-password",MISSING_PASSWORD:"missing-password",INVALID_LOGIN_CREDENTIALS:"invalid-credential",EMAIL_EXISTS:"email-already-in-use",PASSWORD_LOGIN_DISABLED:"operation-not-allowed",INVALID_IDP_RESPONSE:"invalid-credential",INVALID_PENDING_TOKEN:"invalid-credential",FEDERATED_USER_ID_ALREADY_LINKED:"credential-already-in-use",MISSING_REQ_TYPE:"internal-error",EMAIL_NOT_FOUND:"user-not-found",RESET_PASSWORD_EXCEED_LIMIT:"too-many-requests",EXPIRED_OOB_CODE:"expired-action-code",INVALID_OOB_CODE:"invalid-action-code",MISSING_OOB_CODE:"internal-error",CREDENTIAL_TOO_OLD_LOGIN_AGAIN:"requires-recent-login",INVALID_ID_TOKEN:"invalid-user-token",TOKEN_EXPIRED:"user-token-expired",USER_NOT_FOUND:"user-token-expired",TOO_MANY_ATTEMPTS_TRY_LATER:"too-many-requests",PASSWORD_DOES_NOT_MEET_REQUIREMENTS:"password-does-not-meet-requirements",INVALID_CODE:"invalid-verification-code",INVALID_SESSION_INFO:"invalid-verification-id",INVALID_TEMPORARY_PROOF:"invalid-credential",MISSING_SESSION_INFO:"missing-verification-id",SESSION_EXPIRED:"code-expired",MISSING_ANDROID_PACKAGE_NAME:"missing-android-pkg-name",UNAUTHORIZED_DOMAIN:"unauthorized-continue-uri",INVALID_OAUTH_CLIENT_ID:"invalid-oauth-client-id",ADMIN_ONLY_OPERATION:"admin-restricted-operation",INVALID_MFA_PENDING_CREDENTIAL:"invalid-multi-factor-session",MFA_ENROLLMENT_NOT_FOUND:"multi-factor-info-not-found",MISSING_MFA_ENROLLMENT_ID:"missing-multi-factor-info",MISSING_MFA_PENDING_CREDENTIAL:"missing-multi-factor-session",SECOND_FACTOR_EXISTS:"second-factor-already-in-use",SECOND_FACTOR_LIMIT_EXCEEDED:"maximum-second-factor-count-exceeded",BLOCKING_FUNCTION_ERROR_RESPONSE:"internal-error",RECAPTCHA_NOT_ENABLED:"recaptcha-not-enabled",MISSING_RECAPTCHA_TOKEN:"missing-recaptcha-token",INVALID_RECAPTCHA_TOKEN:"invalid-recaptcha-token",INVALID_RECAPTCHA_ACTION:"invalid-recaptcha-action",MISSING_CLIENT_TYPE:"missing-client-type",MISSING_RECAPTCHA_VERSION:"missing-recaptcha-version",INVALID_RECAPTCHA_VERSION:"invalid-recaptcha-version",INVALID_REQ_TYPE:"invalid-req-type"};/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const ua=["/v1/accounts:signInWithCustomToken","/v1/accounts:signInWithEmailLink","/v1/accounts:signInWithIdp","/v1/accounts:signInWithPassword","/v1/accounts:signInWithPhoneNumber","/v1/token"],fa=new pe(3e4,6e4);function Ur(r,e){return r.tenantId&&!e.tenantId?{...e,tenantId:r.tenantId}:e}async function He(r,e,n,o,a={}){return xr(r,a,async()=>{let d={},f={};o&&(e==="GET"?f=o:d={body:JSON.stringify(o)});const v=Sr({key:r.config.apiKey,...f}).slice(1),I=await r._getAdditionalHeaders();I["Content-Type"]="application/json",r.languageCode&&(I["X-Firebase-Locale"]=r.languageCode);const A={method:e,headers:I,...d};return js()||(A.referrerPolicy="no-referrer"),r.emulatorConfig&&br(r.emulatorConfig.host)&&(A.credentials="include"),Mr.fetch()(await Vr(r,r.config.apiHost,n,v),A)})}async function xr(r,e,n){r._canInitEmulator=!1;const o={...la,...e};try{const a=new da(r),d=await Promise.race([n(),a.promise]);a.clearNetworkTimeout();const f=await d.json();if("needConfirmation"in f)throw Pe(r,"account-exists-with-different-credential",f);if(d.ok&&!("errorMessage"in f))return f;{const v=d.ok?f.errorMessage:f.error.message,[I,A]=v.split(" : ");if(I==="FEDERATED_USER_ID_ALREADY_LINKED")throw Pe(r,"credential-already-in-use",f);if(I==="EMAIL_EXISTS")throw Pe(r,"email-already-in-use",f);if(I==="USER_DISABLED")throw Pe(r,"user-disabled",f);const D=o[I]||I.toLowerCase().replace(/[_\s]+/g,"-");if(A)throw Lr(r,D,A);Ji(r,D)}}catch(a){if(a instanceof It)throw a;Ji(r,"network-request-failed",{message:String(a)})}}async function Vr(r,e,n,o){const a=`${e}${n}?${o}`,d=r,f=d.config.emulator?ca(r.config,a):`${r.config.apiScheme}://${a}`;return ua.includes(n)&&(await d._persistenceManagerAvailable,d._getPersistenceType()==="COOKIE")?d._getPersistence()._getFinalTarget(f).toString():f}class da{clearNetworkTimeout(){clearTimeout(this.timer)}constructor(e){this.auth=e,this.timer=null,this.promise=new Promise((n,o)=>{this.timer=setTimeout(()=>o(Or(this.auth,"network-request-failed")),fa.get())})}}function Pe(r,e,n){const o={appName:r.name};n.email&&(o.email=n.email),n.phoneNumber&&(o.phoneNumber=n.phoneNumber);const a=Or(r,e,o);return a.customData._tokenResponse=n,a}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */async function pa(r,e){return He(r,"POST","/v1/accounts:delete",e)}async function Ue(r,e){return He(r,"POST","/v1/accounts:lookup",e)}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function ae(r){if(r)try{const e=new Date(Number(r));if(!isNaN(e.getTime()))return e.toUTCString()}catch{}}async function ga(r,e=!1){const n=de(r),o=await n.getIdToken(e),a=Fr(o);C(a&&a.exp&&a.auth_time&&a.iat,n.auth,"internal-error");const d=typeof a.firebase=="object"?a.firebase:void 0,f=d==null?void 0:d.sign_in_provider;return{claims:a,token:o,authTime:ae(En(a.auth_time)),issuedAtTime:ae(En(a.iat)),expirationTime:ae(En(a.exp)),signInProvider:f||null,signInSecondFactor:(d==null?void 0:d.sign_in_second_factor)||null}}function En(r){return Number(r)*1e3}function Fr(r){const[e,n,o]=r.split(".");if(e===void 0||n===void 0||o===void 0)return De("JWT malformed, contained fewer than 3 sections"),null;try{const a=Tr(n);return a?JSON.parse(a):(De("Failed to decode base64 JWT payload"),null)}catch(a){return De("Caught error parsing JWT payload as JSON",a==null?void 0:a.toString()),null}}function Yi(r){const e=Fr(r);return C(e,"internal-error"),C(typeof e.exp<"u","internal-error"),C(typeof e.iat<"u","internal-error"),Number(e.exp)-Number(e.iat)}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */async function Nn(r,e,n=!1){if(n)return e;try{return await e}catch(o){throw o instanceof It&&ma(o)&&r.auth.currentUser===r&&await r.auth.signOut(),o}}function ma({code:r}){return r==="auth/user-disabled"||r==="auth/user-token-expired"}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class ya{constructor(e){this.user=e,this.isRunning=!1,this.timerId=null,this.errorBackoff=3e4}_start(){this.isRunning||(this.isRunning=!0,this.schedule())}_stop(){this.isRunning&&(this.isRunning=!1,this.timerId!==null&&clearTimeout(this.timerId))}getInterval(e){if(e){const n=this.errorBackoff;return this.errorBackoff=Math.min(this.errorBackoff*2,96e4),n}else{this.errorBackoff=3e4;const o=(this.user.stsTokenManager.expirationTime??0)-Date.now()-3e5;return Math.max(0,o)}}schedule(e=!1){if(!this.isRunning)return;const n=this.getInterval(e);this.timerId=setTimeout(async()=>{await this.iteration()},n)}async iteration(){try{await this.user.getIdToken(!0)}catch(e){(e==null?void 0:e.code)==="auth/network-request-failed"&&this.schedule(!0);return}this.schedule()}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Rn{constructor(e,n){this.createdAt=e,this.lastLoginAt=n,this._initializeTime()}_initializeTime(){this.lastSignInTime=ae(this.lastLoginAt),this.creationTime=ae(this.createdAt)}_copy(e){this.createdAt=e.createdAt,this.lastLoginAt=e.lastLoginAt,this._initializeTime()}toJSON(){return{createdAt:this.createdAt,lastLoginAt:this.lastLoginAt}}}/**
 * @license
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */async function xe(r){var T;const e=r.auth,n=await r.getIdToken(),o=await Nn(r,Ue(e,{idToken:n}));C(o==null?void 0:o.users.length,e,"internal-error");const a=o.users[0];r._notifyReloadListener(a);const d=(T=a.providerUserInfo)!=null&&T.length?jr(a.providerUserInfo):[],f=wa(r.providerData,d),v=r.isAnonymous,I=!(r.email&&a.passwordHash)&&!(f!=null&&f.length),A=v?I:!1,D={uid:a.localId,displayName:a.displayName||null,photoURL:a.photoUrl||null,email:a.email||null,emailVerified:a.emailVerified||!1,phoneNumber:a.phoneNumber||null,tenantId:a.tenantId||null,providerData:f,metadata:new Rn(a.createdAt,a.lastLoginAt),isAnonymous:A};Object.assign(r,D)}async function _a(r){const e=de(r);await xe(e),await e.auth._persistUserIfCurrent(e),e.auth._notifyListenersIfCurrent(e)}function wa(r,e){return[...r.filter(o=>!e.some(a=>a.providerId===o.providerId)),...e]}function jr(r){return r.map(({providerId:e,...n})=>({providerId:e,uid:n.rawId||"",displayName:n.displayName||null,email:n.email||null,phoneNumber:n.phoneNumber||null,photoURL:n.photoUrl||null}))}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */async function va(r,e){const n=await xr(r,{},async()=>{const o=Sr({grant_type:"refresh_token",refresh_token:e}).slice(1),{tokenApiHost:a,apiKey:d}=r.config,f=await Vr(r,a,"/v1/token",`key=${d}`),v=await r._getAdditionalHeaders();v["Content-Type"]="application/x-www-form-urlencoded";const I={method:"POST",headers:v,body:o};return r.emulatorConfig&&br(r.emulatorConfig.host)&&(I.credentials="include"),Mr.fetch()(f,I)});return{accessToken:n.access_token,expiresIn:n.expires_in,refreshToken:n.refresh_token}}async function Ia(r,e){return He(r,"POST","/v2/accounts:revokeToken",Ur(r,e))}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Ft{constructor(){this.refreshToken=null,this.accessToken=null,this.expirationTime=null}get isExpired(){return!this.expirationTime||Date.now()>this.expirationTime-3e4}updateFromServerResponse(e){C(e.idToken,"internal-error"),C(typeof e.idToken<"u","internal-error"),C(typeof e.refreshToken<"u","internal-error");const n="expiresIn"in e&&typeof e.expiresIn<"u"?Number(e.expiresIn):Yi(e.idToken);this.updateTokensAndExpiration(e.idToken,e.refreshToken,n)}updateFromIdToken(e){C(e.length!==0,"internal-error");const n=Yi(e);this.updateTokensAndExpiration(e,null,n)}async getToken(e,n=!1){return!n&&this.accessToken&&!this.isExpired?this.accessToken:(C(this.refreshToken,e,"user-token-expired"),this.refreshToken?(await this.refresh(e,this.refreshToken),this.accessToken):null)}clearRefreshToken(){this.refreshToken=null}async refresh(e,n){const{accessToken:o,refreshToken:a,expiresIn:d}=await va(e,n);this.updateTokensAndExpiration(o,a,Number(d))}updateTokensAndExpiration(e,n,o){this.refreshToken=n||null,this.accessToken=e||null,this.expirationTime=Date.now()+o*1e3}static fromJSON(e,n){const{refreshToken:o,accessToken:a,expirationTime:d}=n,f=new Ft;return o&&(C(typeof o=="string","internal-error",{appName:e}),f.refreshToken=o),a&&(C(typeof a=="string","internal-error",{appName:e}),f.accessToken=a),d&&(C(typeof d=="number","internal-error",{appName:e}),f.expirationTime=d),f}toJSON(){return{refreshToken:this.refreshToken,accessToken:this.accessToken,expirationTime:this.expirationTime}}_assign(e){this.accessToken=e.accessToken,this.refreshToken=e.refreshToken,this.expirationTime=e.expirationTime}_clone(){return Object.assign(new Ft,this.toJSON())}_performRefresh(){return oe("not implemented")}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function yt(r,e){C(typeof r=="string"||typeof r>"u","internal-error",{appName:e})}class it{constructor({uid:e,auth:n,stsTokenManager:o,...a}){this.providerId="firebase",this.proactiveRefresh=new ya(this),this.reloadUserInfo=null,this.reloadListener=null,this.uid=e,this.auth=n,this.stsTokenManager=o,this.accessToken=o.accessToken,this.displayName=a.displayName||null,this.email=a.email||null,this.emailVerified=a.emailVerified||!1,this.phoneNumber=a.phoneNumber||null,this.photoURL=a.photoURL||null,this.isAnonymous=a.isAnonymous||!1,this.tenantId=a.tenantId||null,this.providerData=a.providerData?[...a.providerData]:[],this.metadata=new Rn(a.createdAt||void 0,a.lastLoginAt||void 0)}async getIdToken(e){const n=await Nn(this,this.stsTokenManager.getToken(this.auth,e));return C(n,this.auth,"internal-error"),this.accessToken!==n&&(this.accessToken=n,await this.auth._persistUserIfCurrent(this),this.auth._notifyListenersIfCurrent(this)),n}getIdTokenResult(e){return ga(this,e)}reload(){return _a(this)}_assign(e){this!==e&&(C(this.uid===e.uid,this.auth,"internal-error"),this.displayName=e.displayName,this.photoURL=e.photoURL,this.email=e.email,this.emailVerified=e.emailVerified,this.phoneNumber=e.phoneNumber,this.isAnonymous=e.isAnonymous,this.tenantId=e.tenantId,this.providerData=e.providerData.map(n=>({...n})),this.metadata._copy(e.metadata),this.stsTokenManager._assign(e.stsTokenManager))}_clone(e){const n=new it({...this,auth:e,stsTokenManager:this.stsTokenManager._clone()});return n.metadata._copy(this.metadata),n}_onReload(e){C(!this.reloadListener,this.auth,"internal-error"),this.reloadListener=e,this.reloadUserInfo&&(this._notifyReloadListener(this.reloadUserInfo),this.reloadUserInfo=null)}_notifyReloadListener(e){this.reloadListener?this.reloadListener(e):this.reloadUserInfo=e}_startProactiveRefresh(){this.proactiveRefresh._start()}_stopProactiveRefresh(){this.proactiveRefresh._stop()}async _updateTokensIfNecessary(e,n=!1){let o=!1;e.idToken&&e.idToken!==this.stsTokenManager.accessToken&&(this.stsTokenManager.updateFromServerResponse(e),o=!0),n&&await xe(this),await this.auth._persistUserIfCurrent(this),o&&this.auth._notifyListenersIfCurrent(this)}async delete(){if(Ct(this.auth.app))return Promise.reject(ke(this.auth));const e=await this.getIdToken();return await Nn(this,pa(this.auth,{idToken:e})),this.stsTokenManager.clearRefreshToken(),this.auth.signOut()}toJSON(){return{uid:this.uid,email:this.email||void 0,emailVerified:this.emailVerified,displayName:this.displayName||void 0,isAnonymous:this.isAnonymous,photoURL:this.photoURL||void 0,phoneNumber:this.phoneNumber||void 0,tenantId:this.tenantId||void 0,providerData:this.providerData.map(e=>({...e})),stsTokenManager:this.stsTokenManager.toJSON(),_redirectEventId:this._redirectEventId,...this.metadata.toJSON(),apiKey:this.auth.config.apiKey,appName:this.auth.name}}get refreshToken(){return this.stsTokenManager.refreshToken||""}static _fromJSON(e,n){const o=n.displayName??void 0,a=n.email??void 0,d=n.phoneNumber??void 0,f=n.photoURL??void 0,v=n.tenantId??void 0,I=n._redirectEventId??void 0,A=n.createdAt??void 0,D=n.lastLoginAt??void 0,{uid:T,emailVerified:B,isAnonymous:W,providerData:V,stsTokenManager:j}=n;C(T&&j,e,"internal-error");const L=Ft.fromJSON(this.name,j);C(typeof T=="string",e,"internal-error"),yt(o,e.name),yt(a,e.name),C(typeof B=="boolean",e,"internal-error"),C(typeof W=="boolean",e,"internal-error"),yt(d,e.name),yt(f,e.name),yt(v,e.name),yt(I,e.name),yt(A,e.name),yt(D,e.name);const Q=new it({uid:T,auth:e,email:a,emailVerified:B,displayName:o,isAnonymous:W,photoURL:f,phoneNumber:d,tenantId:v,stsTokenManager:L,createdAt:A,lastLoginAt:D});return V&&Array.isArray(V)&&(Q.providerData=V.map(ht=>({...ht}))),I&&(Q._redirectEventId=I),Q}static async _fromIdTokenResponse(e,n,o=!1){const a=new Ft;a.updateFromServerResponse(n);const d=new it({uid:n.localId,auth:e,stsTokenManager:a,isAnonymous:o});return await xe(d),d}static async _fromGetAccountInfoResponse(e,n,o){const a=n.users[0];C(a.localId!==void 0,"internal-error");const d=a.providerUserInfo!==void 0?jr(a.providerUserInfo):[],f=!(a.email&&a.passwordHash)&&!(d!=null&&d.length),v=new Ft;v.updateFromIdToken(o);const I=new it({uid:a.localId,auth:e,stsTokenManager:v,isAnonymous:f}),A={uid:a.localId,displayName:a.displayName||null,photoURL:a.photoUrl||null,email:a.email||null,emailVerified:a.emailVerified||!1,phoneNumber:a.phoneNumber||null,tenantId:a.tenantId||null,providerData:d,metadata:new Rn(a.createdAt,a.lastLoginAt),isAnonymous:!(a.email&&a.passwordHash)&&!(d!=null&&d.length)};return Object.assign(I,A),I}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Qi=new Map;function Nt(r){Me(r instanceof Function,"Expected a class definition");let e=Qi.get(r);return e?(Me(e instanceof r,"Instance stored in cache mismatched with class"),e):(e=new r,Qi.set(r,e),e)}/**
 * @license
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Br{constructor(){this.type="NONE",this.storage={}}async _isAvailable(){return!0}async _set(e,n){this.storage[e]=n}async _get(e){const n=this.storage[e];return n===void 0?null:n}async _remove(e){delete this.storage[e]}_addListener(e,n){}_removeListener(e,n){}}Br.type="NONE";const Zi=Br;/**
 * @license
 * Copyright 2019 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function An(r,e,n){return`firebase:${r}:${e}:${n}`}class jt{constructor(e,n,o){this.persistence=e,this.auth=n,this.userKey=o;const{config:a,name:d}=this.auth;this.fullUserKey=An(this.userKey,a.apiKey,d),this.fullPersistenceKey=An("persistence",a.apiKey,d),this.boundEventHandler=n._onStorageEvent.bind(n),this.persistence._addListener(this.fullUserKey,this.boundEventHandler)}setCurrentUser(e){return this.persistence._set(this.fullUserKey,e.toJSON())}async getCurrentUser(){const e=await this.persistence._get(this.fullUserKey);if(!e)return null;if(typeof e=="string"){const n=await Ue(this.auth,{idToken:e}).catch(()=>{});return n?it._fromGetAccountInfoResponse(this.auth,n,e):null}return it._fromJSON(this.auth,e)}removeCurrentUser(){return this.persistence._remove(this.fullUserKey)}savePersistenceForRedirect(){return this.persistence._set(this.fullPersistenceKey,this.persistence.type)}async setPersistence(e){if(this.persistence===e)return;const n=await this.getCurrentUser();if(await this.removeCurrentUser(),this.persistence=e,n)return this.setCurrentUser(n)}delete(){this.persistence._removeListener(this.fullUserKey,this.boundEventHandler)}static async create(e,n,o="authUser"){if(!n.length)return new jt(Nt(Zi),e,o);const a=(await Promise.all(n.map(async A=>{if(await A._isAvailable())return A}))).filter(A=>A);let d=a[0]||Nt(Zi);const f=An(o,e.config.apiKey,e.name);let v=null;for(const A of n)try{const D=await A._get(f);if(D){let T;if(typeof D=="string"){const B=await Ue(e,{idToken:D}).catch(()=>{});if(!B)break;T=await it._fromGetAccountInfoResponse(e,B,D)}else T=it._fromJSON(e,D);A!==d&&(v=T),d=A;break}}catch{}const I=a.filter(A=>A._shouldAllowMigration);return!d._shouldAllowMigration||!I.length?new jt(d,e,o):(d=I[0],v&&await d._set(f,v.toJSON()),await Promise.all(n.map(async A=>{if(A!==d)try{await A._remove(f)}catch{}})),new jt(d,e,o))}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function tr(r){const e=r.toLowerCase();if(e.includes("opera/")||e.includes("opr/")||e.includes("opios/"))return"Opera";if(Sa(e))return"IEMobile";if(e.includes("msie")||e.includes("trident/"))return"IE";if(e.includes("edge/"))return"Edge";if(Ea(e))return"Firefox";if(e.includes("silk/"))return"Silk";if(Ca(e))return"Blackberry";if(Pa(e))return"Webos";if(Aa(e))return"Safari";if((e.includes("chrome/")||Ta(e))&&!e.includes("edge/"))return"Chrome";if(ba(e))return"Android";{const n=/([a-zA-Z\d\.]+)\/[a-zA-Z\d\.]*$/,o=r.match(n);if((o==null?void 0:o.length)===2)return o[1]}return"Other"}function Ea(r=st()){return/firefox\//i.test(r)}function Aa(r=st()){const e=r.toLowerCase();return e.includes("safari/")&&!e.includes("chrome/")&&!e.includes("crios/")&&!e.includes("android")}function Ta(r=st()){return/crios\//i.test(r)}function Sa(r=st()){return/iemobile/i.test(r)}function ba(r=st()){return/android/i.test(r)}function Ca(r=st()){return/blackberry/i.test(r)}function Pa(r=st()){return/webos/i.test(r)}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function Hr(r,e=[]){let n;switch(r){case"Browser":n=tr(st());break;case"Worker":n=`${tr(st())}-${r}`;break;default:n=r}const o=e.length?e.join(","):"FirebaseCore-web";return`${n}/JsCore/${Be}/${o}`}/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Na{constructor(e){this.auth=e,this.queue=[]}pushCallback(e,n){const o=d=>new Promise((f,v)=>{try{const I=e(d);f(I)}catch(I){v(I)}});o.onAbort=n,this.queue.push(o);const a=this.queue.length-1;return()=>{this.queue[a]=()=>Promise.resolve()}}async runMiddleware(e){if(this.auth.currentUser===e)return;const n=[];try{for(const o of this.queue)await o(e),o.onAbort&&n.push(o.onAbort)}catch(o){n.reverse();for(const a of n)try{a()}catch{}throw this.auth._errorFactory.create("login-blocked",{originalMessage:o==null?void 0:o.message})}}}/**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */async function Ra(r,e={}){return He(r,"GET","/v2/passwordPolicy",Ur(r,e))}/**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Da=6;class ka{constructor(e){var o;const n=e.customStrengthOptions;this.customStrengthOptions={},this.customStrengthOptions.minPasswordLength=n.minPasswordLength??Da,n.maxPasswordLength&&(this.customStrengthOptions.maxPasswordLength=n.maxPasswordLength),n.containsLowercaseCharacter!==void 0&&(this.customStrengthOptions.containsLowercaseLetter=n.containsLowercaseCharacter),n.containsUppercaseCharacter!==void 0&&(this.customStrengthOptions.containsUppercaseLetter=n.containsUppercaseCharacter),n.containsNumericCharacter!==void 0&&(this.customStrengthOptions.containsNumericCharacter=n.containsNumericCharacter),n.containsNonAlphanumericCharacter!==void 0&&(this.customStrengthOptions.containsNonAlphanumericCharacter=n.containsNonAlphanumericCharacter),this.enforcementState=e.enforcementState,this.enforcementState==="ENFORCEMENT_STATE_UNSPECIFIED"&&(this.enforcementState="OFF"),this.allowedNonAlphanumericCharacters=((o=e.allowedNonAlphanumericCharacters)==null?void 0:o.join(""))??"",this.forceUpgradeOnSignin=e.forceUpgradeOnSignin??!1,this.schemaVersion=e.schemaVersion}validatePassword(e){const n={isValid:!0,passwordPolicy:this};return this.validatePasswordLengthOptions(e,n),this.validatePasswordCharacterOptions(e,n),n.isValid&&(n.isValid=n.meetsMinPasswordLength??!0),n.isValid&&(n.isValid=n.meetsMaxPasswordLength??!0),n.isValid&&(n.isValid=n.containsLowercaseLetter??!0),n.isValid&&(n.isValid=n.containsUppercaseLetter??!0),n.isValid&&(n.isValid=n.containsNumericCharacter??!0),n.isValid&&(n.isValid=n.containsNonAlphanumericCharacter??!0),n}validatePasswordLengthOptions(e,n){const o=this.customStrengthOptions.minPasswordLength,a=this.customStrengthOptions.maxPasswordLength;o&&(n.meetsMinPasswordLength=e.length>=o),a&&(n.meetsMaxPasswordLength=e.length<=a)}validatePasswordCharacterOptions(e,n){this.updatePasswordCharacterOptionsStatuses(n,!1,!1,!1,!1);let o;for(let a=0;a<e.length;a++)o=e.charAt(a),this.updatePasswordCharacterOptionsStatuses(n,o>="a"&&o<="z",o>="A"&&o<="Z",o>="0"&&o<="9",this.allowedNonAlphanumericCharacters.includes(o))}updatePasswordCharacterOptionsStatuses(e,n,o,a,d){this.customStrengthOptions.containsLowercaseLetter&&(e.containsLowercaseLetter||(e.containsLowercaseLetter=n)),this.customStrengthOptions.containsUppercaseLetter&&(e.containsUppercaseLetter||(e.containsUppercaseLetter=o)),this.customStrengthOptions.containsNumericCharacter&&(e.containsNumericCharacter||(e.containsNumericCharacter=a)),this.customStrengthOptions.containsNonAlphanumericCharacter&&(e.containsNonAlphanumericCharacter||(e.containsNonAlphanumericCharacter=d))}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Oa{constructor(e,n,o,a){this.app=e,this.heartbeatServiceProvider=n,this.appCheckServiceProvider=o,this.config=a,this.currentUser=null,this.emulatorConfig=null,this.operations=Promise.resolve(),this.authStateSubscription=new er(this),this.idTokenSubscription=new er(this),this.beforeStateQueue=new Na(this),this.redirectUser=null,this.isProactiveRefreshEnabled=!1,this.EXPECTED_PASSWORD_POLICY_SCHEMA_VERSION=1,this._canInitEmulator=!0,this._isInitialized=!1,this._deleted=!1,this._initializationPromise=null,this._popupRedirectResolver=null,this._errorFactory=kr,this._agentRecaptchaConfig=null,this._tenantRecaptchaConfigs={},this._projectPasswordPolicy=null,this._tenantPasswordPolicies={},this._resolvePersistenceManagerAvailable=void 0,this.lastNotifiedUid=void 0,this.languageCode=null,this.tenantId=null,this.settings={appVerificationDisabledForTesting:!1},this.frameworks=[],this.name=e.name,this.clientVersion=a.sdkClientVersion,this._persistenceManagerAvailable=new Promise(d=>this._resolvePersistenceManagerAvailable=d)}_initializeWithPersistence(e,n){return n&&(this._popupRedirectResolver=Nt(n)),this._initializationPromise=this.queue(async()=>{var o,a,d;if(!this._deleted&&(this.persistenceManager=await jt.create(this,e),(o=this._resolvePersistenceManagerAvailable)==null||o.call(this),!this._deleted)){if((a=this._popupRedirectResolver)!=null&&a._shouldInitProactively)try{await this._popupRedirectResolver._initialize(this)}catch{}await this.initializeCurrentUser(n),this.lastNotifiedUid=((d=this.currentUser)==null?void 0:d.uid)||null,!this._deleted&&(this._isInitialized=!0)}}),this._initializationPromise}async _onStorageEvent(){if(this._deleted)return;const e=await this.assertedPersistence.getCurrentUser();if(!(!this.currentUser&&!e)){if(this.currentUser&&e&&this.currentUser.uid===e.uid){this._currentUser._assign(e),await this.currentUser.getIdToken();return}await this._updateCurrentUser(e,!0)}}async initializeCurrentUserFromIdToken(e){try{const n=await Ue(this,{idToken:e}),o=await it._fromGetAccountInfoResponse(this,n,e);await this.directlySetCurrentUser(o)}catch(n){console.warn("FirebaseServerApp could not login user with provided authIdToken: ",n),await this.directlySetCurrentUser(null)}}async initializeCurrentUser(e){var d;if(Ct(this.app)){const f=this.app.settings.authIdToken;return f?new Promise(v=>{setTimeout(()=>this.initializeCurrentUserFromIdToken(f).then(v,v))}):this.directlySetCurrentUser(null)}const n=await this.assertedPersistence.getCurrentUser();let o=n,a=!1;if(e&&this.config.authDomain){await this.getOrInitRedirectPersistenceManager();const f=(d=this.redirectUser)==null?void 0:d._redirectEventId,v=o==null?void 0:o._redirectEventId,I=await this.tryRedirectSignIn(e);(!f||f===v)&&(I!=null&&I.user)&&(o=I.user,a=!0)}if(!o)return this.directlySetCurrentUser(null);if(!o._redirectEventId){if(a)try{await this.beforeStateQueue.runMiddleware(o)}catch(f){o=n,this._popupRedirectResolver._overrideRedirectResult(this,()=>Promise.reject(f))}return o?this.reloadAndSetCurrentUserOrClear(o):this.directlySetCurrentUser(null)}return C(this._popupRedirectResolver,this,"argument-error"),await this.getOrInitRedirectPersistenceManager(),this.redirectUser&&this.redirectUser._redirectEventId===o._redirectEventId?this.directlySetCurrentUser(o):this.reloadAndSetCurrentUserOrClear(o)}async tryRedirectSignIn(e){let n=null;try{n=await this._popupRedirectResolver._completeRedirectFn(this,e,!0)}catch{await this._setRedirectUser(null)}return n}async reloadAndSetCurrentUserOrClear(e){try{await xe(e)}catch(n){if((n==null?void 0:n.code)!=="auth/network-request-failed")return this.directlySetCurrentUser(null)}return this.directlySetCurrentUser(e)}useDeviceLanguage(){this.languageCode=ha()}async _delete(){this._deleted=!0}async updateCurrentUser(e){if(Ct(this.app))return Promise.reject(ke(this));const n=e?de(e):null;return n&&C(n.auth.config.apiKey===this.config.apiKey,this,"invalid-user-token"),this._updateCurrentUser(n&&n._clone(this))}async _updateCurrentUser(e,n=!1){if(!this._deleted)return e&&C(this.tenantId===e.tenantId,this,"tenant-id-mismatch"),n||await this.beforeStateQueue.runMiddleware(e),this.queue(async()=>{await this.directlySetCurrentUser(e),this.notifyAuthListeners()})}async signOut(){return Ct(this.app)?Promise.reject(ke(this)):(await this.beforeStateQueue.runMiddleware(null),(this.redirectPersistenceManager||this._popupRedirectResolver)&&await this._setRedirectUser(null),this._updateCurrentUser(null,!0))}setPersistence(e){return Ct(this.app)?Promise.reject(ke(this)):this.queue(async()=>{await this.assertedPersistence.setPersistence(Nt(e))})}_getRecaptchaConfig(){return this.tenantId==null?this._agentRecaptchaConfig:this._tenantRecaptchaConfigs[this.tenantId]}async validatePassword(e){this._getPasswordPolicyInternal()||await this._updatePasswordPolicy();const n=this._getPasswordPolicyInternal();return n.schemaVersion!==this.EXPECTED_PASSWORD_POLICY_SCHEMA_VERSION?Promise.reject(this._errorFactory.create("unsupported-password-policy-schema-version",{})):n.validatePassword(e)}_getPasswordPolicyInternal(){return this.tenantId===null?this._projectPasswordPolicy:this._tenantPasswordPolicies[this.tenantId]}async _updatePasswordPolicy(){const e=await Ra(this),n=new ka(e);this.tenantId===null?this._projectPasswordPolicy=n:this._tenantPasswordPolicies[this.tenantId]=n}_getPersistenceType(){return this.assertedPersistence.persistence.type}_getPersistence(){return this.assertedPersistence.persistence}_updateErrorMap(e){this._errorFactory=new fe("auth","Firebase",e())}onAuthStateChanged(e,n,o){return this.registerStateListener(this.authStateSubscription,e,n,o)}beforeAuthStateChanged(e,n){return this.beforeStateQueue.pushCallback(e,n)}onIdTokenChanged(e,n,o){return this.registerStateListener(this.idTokenSubscription,e,n,o)}authStateReady(){return new Promise((e,n)=>{if(this.currentUser)e();else{const o=this.onAuthStateChanged(()=>{o(),e()},n)}})}async revokeAccessToken(e){if(this.currentUser){const n=await this.currentUser.getIdToken(),o={providerId:"apple.com",tokenType:"ACCESS_TOKEN",token:e,idToken:n};this.tenantId!=null&&(o.tenantId=this.tenantId),await Ia(this,o)}}toJSON(){var e;return{apiKey:this.config.apiKey,authDomain:this.config.authDomain,appName:this.name,currentUser:(e=this._currentUser)==null?void 0:e.toJSON()}}async _setRedirectUser(e,n){const o=await this.getOrInitRedirectPersistenceManager(n);return e===null?o.removeCurrentUser():o.setCurrentUser(e)}async getOrInitRedirectPersistenceManager(e){if(!this.redirectPersistenceManager){const n=e&&Nt(e)||this._popupRedirectResolver;C(n,this,"argument-error"),this.redirectPersistenceManager=await jt.create(this,[Nt(n._redirectPersistence)],"redirectUser"),this.redirectUser=await this.redirectPersistenceManager.getCurrentUser()}return this.redirectPersistenceManager}async _redirectUserForId(e){var n,o;return this._isInitialized&&await this.queue(async()=>{}),((n=this._currentUser)==null?void 0:n._redirectEventId)===e?this._currentUser:((o=this.redirectUser)==null?void 0:o._redirectEventId)===e?this.redirectUser:null}async _persistUserIfCurrent(e){if(e===this.currentUser)return this.queue(async()=>this.directlySetCurrentUser(e))}_notifyListenersIfCurrent(e){e===this.currentUser&&this.notifyAuthListeners()}_key(){return`${this.config.authDomain}:${this.config.apiKey}:${this.name}`}_startProactiveRefresh(){this.isProactiveRefreshEnabled=!0,this.currentUser&&this._currentUser._startProactiveRefresh()}_stopProactiveRefresh(){this.isProactiveRefreshEnabled=!1,this.currentUser&&this._currentUser._stopProactiveRefresh()}get _currentUser(){return this.currentUser}notifyAuthListeners(){var n;if(!this._isInitialized)return;this.idTokenSubscription.next(this.currentUser);const e=((n=this.currentUser)==null?void 0:n.uid)??null;this.lastNotifiedUid!==e&&(this.lastNotifiedUid=e,this.authStateSubscription.next(this.currentUser))}registerStateListener(e,n,o,a){if(this._deleted)return()=>{};const d=typeof n=="function"?n:n.next.bind(n);let f=!1;const v=this._isInitialized?Promise.resolve():this._initializationPromise;if(C(v,this,"internal-error"),v.then(()=>{f||d(this.currentUser)}),typeof n=="function"){const I=e.addObserver(n,o,a);return()=>{f=!0,I()}}else{const I=e.addObserver(n);return()=>{f=!0,I()}}}async directlySetCurrentUser(e){this.currentUser&&this.currentUser!==e&&this._currentUser._stopProactiveRefresh(),e&&this.isProactiveRefreshEnabled&&e._startProactiveRefresh(),this.currentUser=e,e?await this.assertedPersistence.setCurrentUser(e):await this.assertedPersistence.removeCurrentUser()}queue(e){return this.operations=this.operations.then(e,e),this.operations}get assertedPersistence(){return C(this.persistenceManager,this,"internal-error"),this.persistenceManager}_logFramework(e){!e||this.frameworks.includes(e)||(this.frameworks.push(e),this.frameworks.sort(),this.clientVersion=Hr(this.config.clientPlatform,this._getFrameworks()))}_getFrameworks(){return this.frameworks}async _getAdditionalHeaders(){var a;const e={"X-Client-Version":this.clientVersion};this.app.options.appId&&(e["X-Firebase-gmpid"]=this.app.options.appId);const n=await((a=this.heartbeatServiceProvider.getImmediate({optional:!0}))==null?void 0:a.getHeartbeatsHeader());n&&(e["X-Firebase-Client"]=n);const o=await this._getAppCheckToken();return o&&(e["X-Firebase-AppCheck"]=o),e}async _getAppCheckToken(){var n;if(Ct(this.app)&&this.app.settings.appCheckToken)return this.app.settings.appCheckToken;const e=await((n=this.appCheckServiceProvider.getImmediate({optional:!0}))==null?void 0:n.getToken());return e!=null&&e.error&&sa(`Error while retrieving App Check token: ${e.error}`),e==null?void 0:e.token}}function La(r){return de(r)}class er{constructor(e){this.auth=e,this.observer=null,this.addObserver=Ks(n=>this.observer=n)}get next(){return C(this.observer,this.auth,"internal-error"),this.observer.next.bind(this.observer)}}function Ma(r,e){const n=(e==null?void 0:e.persistence)||[],o=(Array.isArray(n)?n:[n]).map(Nt);e!=null&&e.errorMap&&r._updateErrorMap(e.errorMap),r._initializeWithPersistence(o,e==null?void 0:e.popupRedirectResolver)}new pe(3e4,6e4);/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */new pe(2e3,1e4);/**
 * @license
 * Copyright 2020 Google LLC.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */new pe(3e4,6e4);/**
 * @license
 * Copyright 2020 Google LLC.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */new pe(5e3,15e3);var nr="@firebase/auth",ir="1.13.1";/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Ua{constructor(e){this.auth=e,this.internalListeners=new Map}getUid(){var e;return this.assertAuthConfigured(),((e=this.auth.currentUser)==null?void 0:e.uid)||null}async getToken(e){return this.assertAuthConfigured(),await this.auth._initializationPromise,this.auth.currentUser?{accessToken:await this.auth.currentUser.getIdToken(e)}:null}addAuthTokenListener(e){if(this.assertAuthConfigured(),this.internalListeners.has(e))return;const n=this.auth.onIdTokenChanged(o=>{e((o==null?void 0:o.stsTokenManager.accessToken)||null)});this.internalListeners.set(e,n),this.updateProactiveRefresh()}removeAuthTokenListener(e){this.assertAuthConfigured();const n=this.internalListeners.get(e);n&&(this.internalListeners.delete(e),n(),this.updateProactiveRefresh())}assertAuthConfigured(){C(this.auth._initializationPromise,"dependent-sdk-initialized-before-auth")}updateProactiveRefresh(){this.internalListeners.size>0?this.auth._startProactiveRefresh():this.auth._stopProactiveRefresh()}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function xa(r){switch(r){case"Node":return"node";case"ReactNative":return"rn";case"Worker":return"webworker";case"Cordova":return"cordova";case"WebExtension":return"web-extension";default:return}}function Va(r){$t(new Ht("auth",(e,{options:n})=>{const o=e.getProvider("app").getImmediate(),a=e.getProvider("heartbeat"),d=e.getProvider("app-check-internal"),{apiKey:f,authDomain:v}=o.options;C(f&&!f.includes(":"),"invalid-api-key",{appName:o.name});const I={apiKey:f,authDomain:v,clientPlatform:r,apiHost:"identitytoolkit.googleapis.com",tokenApiHost:"securetoken.googleapis.com",apiScheme:"https",sdkClientVersion:Hr(r)},A=new Oa(o,a,d,I);return Ma(A,n),A},"PUBLIC").setInstantiationMode("EXPLICIT").setInstanceCreatedCallback((e,n,o)=>{e.getProvider("auth-internal").initialize()})),$t(new Ht("auth-internal",e=>{const n=La(e.getProvider("auth").getImmediate());return(o=>new Ua(o))(n)},"PRIVATE").setInstantiationMode("EXPLICIT")),wt(nr,ir,xa(r)),wt(nr,ir,"esm2020")}/**
 * @license
 * Copyright 2021 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Fa=300;Vs("authIdTokenMaxAge");Va("Browser");var rr=typeof globalThis<"u"?globalThis:typeof window<"u"?window:typeof global<"u"?global:typeof self<"u"?self:{};/** @license
Copyright The Closure Library Authors.
SPDX-License-Identifier: Apache-2.0
*/var Un;(function(){var r;/** @license

 Copyright The Closure Library Authors.
 SPDX-License-Identifier: Apache-2.0
*/function e(g,c){function u(){}u.prototype=c.prototype,g.F=c.prototype,g.prototype=new u,g.prototype.constructor=g,g.D=function(m,p,_){for(var l=Array(arguments.length-2),z=2;z<arguments.length;z++)l[z-2]=arguments[z];return c.prototype[p].apply(m,l)}}function n(){this.blockSize=-1}function o(){this.blockSize=-1,this.blockSize=64,this.g=Array(4),this.C=Array(this.blockSize),this.o=this.h=0,this.u()}e(o,n),o.prototype.u=function(){this.g[0]=1732584193,this.g[1]=4023233417,this.g[2]=2562383102,this.g[3]=271733878,this.o=this.h=0};function a(g,c,u){u||(u=0);const m=Array(16);if(typeof c=="string")for(var p=0;p<16;++p)m[p]=c.charCodeAt(u++)|c.charCodeAt(u++)<<8|c.charCodeAt(u++)<<16|c.charCodeAt(u++)<<24;else for(p=0;p<16;++p)m[p]=c[u++]|c[u++]<<8|c[u++]<<16|c[u++]<<24;c=g.g[0],u=g.g[1],p=g.g[2];let _=g.g[3],l;l=c+(_^u&(p^_))+m[0]+3614090360&4294967295,c=u+(l<<7&4294967295|l>>>25),l=_+(p^c&(u^p))+m[1]+3905402710&4294967295,_=c+(l<<12&4294967295|l>>>20),l=p+(u^_&(c^u))+m[2]+606105819&4294967295,p=_+(l<<17&4294967295|l>>>15),l=u+(c^p&(_^c))+m[3]+3250441966&4294967295,u=p+(l<<22&4294967295|l>>>10),l=c+(_^u&(p^_))+m[4]+4118548399&4294967295,c=u+(l<<7&4294967295|l>>>25),l=_+(p^c&(u^p))+m[5]+1200080426&4294967295,_=c+(l<<12&4294967295|l>>>20),l=p+(u^_&(c^u))+m[6]+2821735955&4294967295,p=_+(l<<17&4294967295|l>>>15),l=u+(c^p&(_^c))+m[7]+4249261313&4294967295,u=p+(l<<22&4294967295|l>>>10),l=c+(_^u&(p^_))+m[8]+1770035416&4294967295,c=u+(l<<7&4294967295|l>>>25),l=_+(p^c&(u^p))+m[9]+2336552879&4294967295,_=c+(l<<12&4294967295|l>>>20),l=p+(u^_&(c^u))+m[10]+4294925233&4294967295,p=_+(l<<17&4294967295|l>>>15),l=u+(c^p&(_^c))+m[11]+2304563134&4294967295,u=p+(l<<22&4294967295|l>>>10),l=c+(_^u&(p^_))+m[12]+1804603682&4294967295,c=u+(l<<7&4294967295|l>>>25),l=_+(p^c&(u^p))+m[13]+4254626195&4294967295,_=c+(l<<12&4294967295|l>>>20),l=p+(u^_&(c^u))+m[14]+2792965006&4294967295,p=_+(l<<17&4294967295|l>>>15),l=u+(c^p&(_^c))+m[15]+1236535329&4294967295,u=p+(l<<22&4294967295|l>>>10),l=c+(p^_&(u^p))+m[1]+4129170786&4294967295,c=u+(l<<5&4294967295|l>>>27),l=_+(u^p&(c^u))+m[6]+3225465664&4294967295,_=c+(l<<9&4294967295|l>>>23),l=p+(c^u&(_^c))+m[11]+643717713&4294967295,p=_+(l<<14&4294967295|l>>>18),l=u+(_^c&(p^_))+m[0]+3921069994&4294967295,u=p+(l<<20&4294967295|l>>>12),l=c+(p^_&(u^p))+m[5]+3593408605&4294967295,c=u+(l<<5&4294967295|l>>>27),l=_+(u^p&(c^u))+m[10]+38016083&4294967295,_=c+(l<<9&4294967295|l>>>23),l=p+(c^u&(_^c))+m[15]+3634488961&4294967295,p=_+(l<<14&4294967295|l>>>18),l=u+(_^c&(p^_))+m[4]+3889429448&4294967295,u=p+(l<<20&4294967295|l>>>12),l=c+(p^_&(u^p))+m[9]+568446438&4294967295,c=u+(l<<5&4294967295|l>>>27),l=_+(u^p&(c^u))+m[14]+3275163606&4294967295,_=c+(l<<9&4294967295|l>>>23),l=p+(c^u&(_^c))+m[3]+4107603335&4294967295,p=_+(l<<14&4294967295|l>>>18),l=u+(_^c&(p^_))+m[8]+1163531501&4294967295,u=p+(l<<20&4294967295|l>>>12),l=c+(p^_&(u^p))+m[13]+2850285829&4294967295,c=u+(l<<5&4294967295|l>>>27),l=_+(u^p&(c^u))+m[2]+4243563512&4294967295,_=c+(l<<9&4294967295|l>>>23),l=p+(c^u&(_^c))+m[7]+1735328473&4294967295,p=_+(l<<14&4294967295|l>>>18),l=u+(_^c&(p^_))+m[12]+2368359562&4294967295,u=p+(l<<20&4294967295|l>>>12),l=c+(u^p^_)+m[5]+4294588738&4294967295,c=u+(l<<4&4294967295|l>>>28),l=_+(c^u^p)+m[8]+2272392833&4294967295,_=c+(l<<11&4294967295|l>>>21),l=p+(_^c^u)+m[11]+1839030562&4294967295,p=_+(l<<16&4294967295|l>>>16),l=u+(p^_^c)+m[14]+4259657740&4294967295,u=p+(l<<23&4294967295|l>>>9),l=c+(u^p^_)+m[1]+2763975236&4294967295,c=u+(l<<4&4294967295|l>>>28),l=_+(c^u^p)+m[4]+1272893353&4294967295,_=c+(l<<11&4294967295|l>>>21),l=p+(_^c^u)+m[7]+4139469664&4294967295,p=_+(l<<16&4294967295|l>>>16),l=u+(p^_^c)+m[10]+3200236656&4294967295,u=p+(l<<23&4294967295|l>>>9),l=c+(u^p^_)+m[13]+681279174&4294967295,c=u+(l<<4&4294967295|l>>>28),l=_+(c^u^p)+m[0]+3936430074&4294967295,_=c+(l<<11&4294967295|l>>>21),l=p+(_^c^u)+m[3]+3572445317&4294967295,p=_+(l<<16&4294967295|l>>>16),l=u+(p^_^c)+m[6]+76029189&4294967295,u=p+(l<<23&4294967295|l>>>9),l=c+(u^p^_)+m[9]+3654602809&4294967295,c=u+(l<<4&4294967295|l>>>28),l=_+(c^u^p)+m[12]+3873151461&4294967295,_=c+(l<<11&4294967295|l>>>21),l=p+(_^c^u)+m[15]+530742520&4294967295,p=_+(l<<16&4294967295|l>>>16),l=u+(p^_^c)+m[2]+3299628645&4294967295,u=p+(l<<23&4294967295|l>>>9),l=c+(p^(u|~_))+m[0]+4096336452&4294967295,c=u+(l<<6&4294967295|l>>>26),l=_+(u^(c|~p))+m[7]+1126891415&4294967295,_=c+(l<<10&4294967295|l>>>22),l=p+(c^(_|~u))+m[14]+2878612391&4294967295,p=_+(l<<15&4294967295|l>>>17),l=u+(_^(p|~c))+m[5]+4237533241&4294967295,u=p+(l<<21&4294967295|l>>>11),l=c+(p^(u|~_))+m[12]+1700485571&4294967295,c=u+(l<<6&4294967295|l>>>26),l=_+(u^(c|~p))+m[3]+2399980690&4294967295,_=c+(l<<10&4294967295|l>>>22),l=p+(c^(_|~u))+m[10]+4293915773&4294967295,p=_+(l<<15&4294967295|l>>>17),l=u+(_^(p|~c))+m[1]+2240044497&4294967295,u=p+(l<<21&4294967295|l>>>11),l=c+(p^(u|~_))+m[8]+1873313359&4294967295,c=u+(l<<6&4294967295|l>>>26),l=_+(u^(c|~p))+m[15]+4264355552&4294967295,_=c+(l<<10&4294967295|l>>>22),l=p+(c^(_|~u))+m[6]+2734768916&4294967295,p=_+(l<<15&4294967295|l>>>17),l=u+(_^(p|~c))+m[13]+1309151649&4294967295,u=p+(l<<21&4294967295|l>>>11),l=c+(p^(u|~_))+m[4]+4149444226&4294967295,c=u+(l<<6&4294967295|l>>>26),l=_+(u^(c|~p))+m[11]+3174756917&4294967295,_=c+(l<<10&4294967295|l>>>22),l=p+(c^(_|~u))+m[2]+718787259&4294967295,p=_+(l<<15&4294967295|l>>>17),l=u+(_^(p|~c))+m[9]+3951481745&4294967295,g.g[0]=g.g[0]+c&4294967295,g.g[1]=g.g[1]+(p+(l<<21&4294967295|l>>>11))&4294967295,g.g[2]=g.g[2]+p&4294967295,g.g[3]=g.g[3]+_&4294967295}o.prototype.v=function(g,c){c===void 0&&(c=g.length);const u=c-this.blockSize,m=this.C;let p=this.h,_=0;for(;_<c;){if(p==0)for(;_<=u;)a(this,g,_),_+=this.blockSize;if(typeof g=="string"){for(;_<c;)if(m[p++]=g.charCodeAt(_++),p==this.blockSize){a(this,m),p=0;break}}else for(;_<c;)if(m[p++]=g[_++],p==this.blockSize){a(this,m),p=0;break}}this.h=p,this.o+=c},o.prototype.A=function(){var g=Array((this.h<56?this.blockSize:this.blockSize*2)-this.h);g[0]=128;for(var c=1;c<g.length-8;++c)g[c]=0;c=this.o*8;for(var u=g.length-8;u<g.length;++u)g[u]=c&255,c/=256;for(this.v(g),g=Array(16),c=0,u=0;u<4;++u)for(let m=0;m<32;m+=8)g[c++]=this.g[u]>>>m&255;return g};function d(g,c){var u=v;return Object.prototype.hasOwnProperty.call(u,g)?u[g]:u[g]=c(g)}function f(g,c){this.h=c;const u=[];let m=!0;for(let p=g.length-1;p>=0;p--){const _=g[p]|0;m&&_==c||(u[p]=_,m=!1)}this.g=u}var v={};function I(g){return-128<=g&&g<128?d(g,function(c){return new f([c|0],c<0?-1:0)}):new f([g|0],g<0?-1:0)}function A(g){if(isNaN(g)||!isFinite(g))return T;if(g<0)return L(A(-g));const c=[];let u=1;for(let m=0;g>=u;m++)c[m]=g/u|0,u*=4294967296;return new f(c,0)}function D(g,c){if(g.length==0)throw Error("number format error: empty string");if(c=c||10,c<2||36<c)throw Error("radix out of range: "+c);if(g.charAt(0)=="-")return L(D(g.substring(1),c));if(g.indexOf("-")>=0)throw Error('number format error: interior "-" character');const u=A(Math.pow(c,8));let m=T;for(let _=0;_<g.length;_+=8){var p=Math.min(8,g.length-_);const l=parseInt(g.substring(_,_+p),c);p<8?(p=A(Math.pow(c,p)),m=m.j(p).add(A(l))):(m=m.j(u),m=m.add(A(l)))}return m}var T=I(0),B=I(1),W=I(16777216);r=f.prototype,r.m=function(){if(j(this))return-L(this).m();let g=0,c=1;for(let u=0;u<this.g.length;u++){const m=this.i(u);g+=(m>=0?m:4294967296+m)*c,c*=4294967296}return g},r.toString=function(g){if(g=g||10,g<2||36<g)throw Error("radix out of range: "+g);if(V(this))return"0";if(j(this))return"-"+L(this).toString(g);const c=A(Math.pow(g,6));var u=this;let m="";for(;;){const p=Lt(u,c).g;u=Q(u,p.j(c));let _=((u.g.length>0?u.g[0]:u.h)>>>0).toString(g);if(u=p,V(u))return _+m;for(;_.length<6;)_="0"+_;m=_+m}},r.i=function(g){return g<0?0:g<this.g.length?this.g[g]:this.h};function V(g){if(g.h!=0)return!1;for(let c=0;c<g.g.length;c++)if(g.g[c]!=0)return!1;return!0}function j(g){return g.h==-1}r.l=function(g){return g=Q(this,g),j(g)?-1:V(g)?0:1};function L(g){const c=g.g.length,u=[];for(let m=0;m<c;m++)u[m]=~g.g[m];return new f(u,~g.h).add(B)}r.abs=function(){return j(this)?L(this):this},r.add=function(g){const c=Math.max(this.g.length,g.g.length),u=[];let m=0;for(let p=0;p<=c;p++){let _=m+(this.i(p)&65535)+(g.i(p)&65535),l=(_>>>16)+(this.i(p)>>>16)+(g.i(p)>>>16);m=l>>>16,_&=65535,l&=65535,u[p]=l<<16|_}return new f(u,u[u.length-1]&-2147483648?-1:0)};function Q(g,c){return g.add(L(c))}r.j=function(g){if(V(this)||V(g))return T;if(j(this))return j(g)?L(this).j(L(g)):L(L(this).j(g));if(j(g))return L(this.j(L(g)));if(this.l(W)<0&&g.l(W)<0)return A(this.m()*g.m());const c=this.g.length+g.g.length,u=[];for(var m=0;m<2*c;m++)u[m]=0;for(m=0;m<this.g.length;m++)for(let p=0;p<g.g.length;p++){const _=this.i(m)>>>16,l=this.i(m)&65535,z=g.i(p)>>>16,Et=g.i(p)&65535;u[2*m+2*p]+=l*Et,ht(u,2*m+2*p),u[2*m+2*p+1]+=_*Et,ht(u,2*m+2*p+1),u[2*m+2*p+1]+=l*z,ht(u,2*m+2*p+1),u[2*m+2*p+2]+=_*z,ht(u,2*m+2*p+2)}for(g=0;g<c;g++)u[g]=u[2*g+1]<<16|u[2*g];for(g=c;g<2*c;g++)u[g]=0;return new f(u,0)};function ht(g,c){for(;(g[c]&65535)!=g[c];)g[c+1]+=g[c]>>>16,g[c]&=65535,c++}function ct(g,c){this.g=g,this.h=c}function Lt(g,c){if(V(c))throw Error("division by zero");if(V(g))return new ct(T,T);if(j(g))return c=Lt(L(g),c),new ct(L(c.g),L(c.h));if(j(c))return c=Lt(g,L(c)),new ct(L(c.g),c.h);if(g.g.length>30){if(j(g)||j(c))throw Error("slowDivide_ only works with positive integers.");for(var u=B,m=c;m.l(g)<=0;)u=lt(u),m=lt(m);var p=K(u,1),_=K(m,1);for(m=K(m,2),u=K(u,2);!V(m);){var l=_.add(m);l.l(g)<=0&&(p=p.add(u),_=l),m=K(m,1),u=K(u,1)}return c=Q(g,p.j(c)),new ct(p,c)}for(p=T;g.l(c)>=0;){for(u=Math.max(1,Math.floor(g.m()/c.m())),m=Math.ceil(Math.log(u)/Math.LN2),m=m<=48?1:Math.pow(2,m-48),_=A(u),l=_.j(c);j(l)||l.l(g)>0;)u-=m,_=A(u),l=_.j(c);V(_)&&(_=B),p=p.add(_),g=Q(g,l)}return new ct(p,g)}r.B=function(g){return Lt(this,g).h},r.and=function(g){const c=Math.max(this.g.length,g.g.length),u=[];for(let m=0;m<c;m++)u[m]=this.i(m)&g.i(m);return new f(u,this.h&g.h)},r.or=function(g){const c=Math.max(this.g.length,g.g.length),u=[];for(let m=0;m<c;m++)u[m]=this.i(m)|g.i(m);return new f(u,this.h|g.h)},r.xor=function(g){const c=Math.max(this.g.length,g.g.length),u=[];for(let m=0;m<c;m++)u[m]=this.i(m)^g.i(m);return new f(u,this.h^g.h)};function lt(g){const c=g.g.length+1,u=[];for(let m=0;m<c;m++)u[m]=g.i(m)<<1|g.i(m-1)>>>31;return new f(u,g.h)}function K(g,c){const u=c>>5;c%=32;const m=g.g.length-u,p=[];for(let _=0;_<m;_++)p[_]=c>0?g.i(_+u)>>>c|g.i(_+u+1)<<32-c:g.i(_+u);return new f(p,g.h)}o.prototype.digest=o.prototype.A,o.prototype.reset=o.prototype.u,o.prototype.update=o.prototype.v,f.prototype.add=f.prototype.add,f.prototype.multiply=f.prototype.j,f.prototype.modulo=f.prototype.B,f.prototype.compare=f.prototype.l,f.prototype.toNumber=f.prototype.m,f.prototype.toString=f.prototype.toString,f.prototype.getBits=f.prototype.i,f.fromNumber=A,f.fromString=D,Un=f}).apply(typeof rr<"u"?rr:typeof self<"u"?self:typeof window<"u"?window:{});var Ne=typeof globalThis<"u"?globalThis:typeof window<"u"?window:typeof global<"u"?global:typeof self<"u"?self:{};(function(){var r,e=Object.defineProperty;function n(t){t=[typeof globalThis=="object"&&globalThis,t,typeof window=="object"&&window,typeof self=="object"&&self,typeof Ne=="object"&&Ne];for(var i=0;i<t.length;++i){var s=t[i];if(s&&s.Math==Math)return s}throw Error("Cannot find global object")}var o=n(this);function a(t,i){if(i)t:{var s=o;t=t.split(".");for(var h=0;h<t.length-1;h++){var y=t[h];if(!(y in s))break t;s=s[y]}t=t[t.length-1],h=s[t],i=i(h),i!=h&&i!=null&&e(s,t,{configurable:!0,writable:!0,value:i})}}a("Symbol.dispose",function(t){return t||Symbol("Symbol.dispose")}),a("Array.prototype.values",function(t){return t||function(){return this[Symbol.iterator]()}}),a("Object.entries",function(t){return t||function(i){var s=[],h;for(h in i)Object.prototype.hasOwnProperty.call(i,h)&&s.push([h,i[h]]);return s}});/** @license

 Copyright The Closure Library Authors.
 SPDX-License-Identifier: Apache-2.0
*/var d=d||{},f=this||self;function v(t){var i=typeof t;return i=="object"&&t!=null||i=="function"}function I(t,i,s){return t.call.apply(t.bind,arguments)}function A(t,i,s){return A=I,A.apply(null,arguments)}function D(t,i){var s=Array.prototype.slice.call(arguments,1);return function(){var h=s.slice();return h.push.apply(h,arguments),t.apply(this,h)}}function T(t,i){function s(){}s.prototype=i.prototype,t.Z=i.prototype,t.prototype=new s,t.prototype.constructor=t,t.Ob=function(h,y,w){for(var E=Array(arguments.length-2),S=2;S<arguments.length;S++)E[S-2]=arguments[S];return i.prototype[y].apply(h,E)}}var B=typeof AsyncContext<"u"&&typeof AsyncContext.Snapshot=="function"?t=>t&&AsyncContext.Snapshot.wrap(t):t=>t;function W(t){const i=t.length;if(i>0){const s=Array(i);for(let h=0;h<i;h++)s[h]=t[h];return s}return[]}function V(t,i){for(let h=1;h<arguments.length;h++){const y=arguments[h];var s=typeof y;if(s=s!="object"?s:y?Array.isArray(y)?"array":s:"null",s=="array"||s=="object"&&typeof y.length=="number"){s=t.length||0;const w=y.length||0;t.length=s+w;for(let E=0;E<w;E++)t[s+E]=y[E]}else t.push(y)}}class j{constructor(i,s){this.i=i,this.j=s,this.h=0,this.g=null}get(){let i;return this.h>0?(this.h--,i=this.g,this.g=i.next,i.next=null):i=this.i(),i}}function L(t){f.setTimeout(()=>{throw t},0)}function Q(){var t=g;let i=null;return t.g&&(i=t.g,t.g=t.g.next,t.g||(t.h=null),i.next=null),i}class ht{constructor(){this.h=this.g=null}add(i,s){const h=ct.get();h.set(i,s),this.h?this.h.next=h:this.g=h,this.h=h}}var ct=new j(()=>new Lt,t=>t.reset());class Lt{constructor(){this.next=this.g=this.h=null}set(i,s){this.h=i,this.g=s,this.next=null}reset(){this.next=this.g=this.h=null}}let lt,K=!1,g=new ht,c=()=>{const t=Promise.resolve(void 0);lt=()=>{t.then(u)}};function u(){for(var t;t=Q();){try{t.h.call(t.g)}catch(s){L(s)}var i=ct;i.j(t),i.h<100&&(i.h++,t.next=i.g,i.g=t)}K=!1}function m(){this.u=this.u,this.C=this.C}m.prototype.u=!1,m.prototype.dispose=function(){this.u||(this.u=!0,this.N())},m.prototype[Symbol.dispose]=function(){this.dispose()},m.prototype.N=function(){if(this.C)for(;this.C.length;)this.C.shift()()};function p(t,i){this.type=t,this.g=this.target=i,this.defaultPrevented=!1}p.prototype.h=function(){this.defaultPrevented=!0};var _=(function(){if(!f.addEventListener||!Object.defineProperty)return!1;var t=!1,i=Object.defineProperty({},"passive",{get:function(){t=!0}});try{const s=()=>{};f.addEventListener("test",s,i),f.removeEventListener("test",s,i)}catch{}return t})();function l(t){return/^[\s\xa0]*$/.test(t)}function z(t,i){p.call(this,t?t.type:""),this.relatedTarget=this.g=this.target=null,this.button=this.screenY=this.screenX=this.clientY=this.clientX=0,this.key="",this.metaKey=this.shiftKey=this.altKey=this.ctrlKey=!1,this.state=null,this.pointerId=0,this.pointerType="",this.i=null,t&&this.init(t,i)}T(z,p),z.prototype.init=function(t,i){const s=this.type=t.type,h=t.changedTouches&&t.changedTouches.length?t.changedTouches[0]:null;this.target=t.target||t.srcElement,this.g=i,i=t.relatedTarget,i||(s=="mouseover"?i=t.fromElement:s=="mouseout"&&(i=t.toElement)),this.relatedTarget=i,h?(this.clientX=h.clientX!==void 0?h.clientX:h.pageX,this.clientY=h.clientY!==void 0?h.clientY:h.pageY,this.screenX=h.screenX||0,this.screenY=h.screenY||0):(this.clientX=t.clientX!==void 0?t.clientX:t.pageX,this.clientY=t.clientY!==void 0?t.clientY:t.pageY,this.screenX=t.screenX||0,this.screenY=t.screenY||0),this.button=t.button,this.key=t.key||"",this.ctrlKey=t.ctrlKey,this.altKey=t.altKey,this.shiftKey=t.shiftKey,this.metaKey=t.metaKey,this.pointerId=t.pointerId||0,this.pointerType=t.pointerType,this.state=t.state,this.i=t,t.defaultPrevented&&z.Z.h.call(this)},z.prototype.h=function(){z.Z.h.call(this);const t=this.i;t.preventDefault?t.preventDefault():t.returnValue=!1};var Et="closure_listenable_"+(Math.random()*1e6|0),Jr=0;function Xr(t,i,s,h,y){this.listener=t,this.proxy=null,this.src=i,this.type=s,this.capture=!!h,this.ha=y,this.key=++Jr,this.da=this.fa=!1}function me(t){t.da=!0,t.listener=null,t.proxy=null,t.src=null,t.ha=null}function ye(t,i,s){for(const h in t)i.call(s,t[h],h,t)}function Yr(t,i){for(const s in t)i.call(void 0,t[s],s,t)}function jn(t){const i={};for(const s in t)i[s]=t[s];return i}const Bn="constructor hasOwnProperty isPrototypeOf propertyIsEnumerable toLocaleString toString valueOf".split(" ");function Hn(t,i){let s,h;for(let y=1;y<arguments.length;y++){h=arguments[y];for(s in h)t[s]=h[s];for(let w=0;w<Bn.length;w++)s=Bn[w],Object.prototype.hasOwnProperty.call(h,s)&&(t[s]=h[s])}}function _e(t){this.src=t,this.g={},this.h=0}_e.prototype.add=function(t,i,s,h,y){const w=t.toString();t=this.g[w],t||(t=this.g[w]=[],this.h++);const E=We(t,i,h,y);return E>-1?(i=t[E],s||(i.fa=!1)):(i=new Xr(i,this.src,w,!!h,y),i.fa=s,t.push(i)),i};function Ge(t,i){const s=i.type;if(s in t.g){var h=t.g[s],y=Array.prototype.indexOf.call(h,i,void 0),w;(w=y>=0)&&Array.prototype.splice.call(h,y,1),w&&(me(i),t.g[s].length==0&&(delete t.g[s],t.h--))}}function We(t,i,s,h){for(let y=0;y<t.length;++y){const w=t[y];if(!w.da&&w.listener==i&&w.capture==!!s&&w.ha==h)return y}return-1}var ze="closure_lm_"+(Math.random()*1e6|0),qe={};function $n(t,i,s,h,y){if(Array.isArray(i)){for(let w=0;w<i.length;w++)$n(t,i[w],s,h,y);return null}return s=zn(s),t&&t[Et]?t.J(i,s,v(h)?!!h.capture:!1,y):Qr(t,i,s,!1,h,y)}function Qr(t,i,s,h,y,w){if(!i)throw Error("Invalid event type");const E=v(y)?!!y.capture:!!y;let S=Je(t);if(S||(t[ze]=S=new _e(t)),s=S.add(i,s,h,E,w),s.proxy)return s;if(h=Zr(),s.proxy=h,h.src=t,h.listener=s,t.addEventListener)_||(y=E),y===void 0&&(y=!1),t.addEventListener(i.toString(),h,y);else if(t.attachEvent)t.attachEvent(Wn(i.toString()),h);else if(t.addListener&&t.removeListener)t.addListener(h);else throw Error("addEventListener and attachEvent are unavailable.");return s}function Zr(){function t(s){return i.call(t.src,t.listener,s)}const i=ts;return t}function Gn(t,i,s,h,y){if(Array.isArray(i))for(var w=0;w<i.length;w++)Gn(t,i[w],s,h,y);else h=v(h)?!!h.capture:!!h,s=zn(s),t&&t[Et]?(t=t.i,w=String(i).toString(),w in t.g&&(i=t.g[w],s=We(i,s,h,y),s>-1&&(me(i[s]),Array.prototype.splice.call(i,s,1),i.length==0&&(delete t.g[w],t.h--)))):t&&(t=Je(t))&&(i=t.g[i.toString()],t=-1,i&&(t=We(i,s,h,y)),(s=t>-1?i[t]:null)&&Ke(s))}function Ke(t){if(typeof t!="number"&&t&&!t.da){var i=t.src;if(i&&i[Et])Ge(i.i,t);else{var s=t.type,h=t.proxy;i.removeEventListener?i.removeEventListener(s,h,t.capture):i.detachEvent?i.detachEvent(Wn(s),h):i.addListener&&i.removeListener&&i.removeListener(h),(s=Je(i))?(Ge(s,t),s.h==0&&(s.src=null,i[ze]=null)):me(t)}}}function Wn(t){return t in qe?qe[t]:qe[t]="on"+t}function ts(t,i){if(t.da)t=!0;else{i=new z(i,this);const s=t.listener,h=t.ha||t.src;t.fa&&Ke(t),t=s.call(h,i)}return t}function Je(t){return t=t[ze],t instanceof _e?t:null}var Xe="__closure_events_fn_"+(Math.random()*1e9>>>0);function zn(t){return typeof t=="function"?t:(t[Xe]||(t[Xe]=function(i){return t.handleEvent(i)}),t[Xe])}function H(){m.call(this),this.i=new _e(this),this.M=this,this.G=null}T(H,m),H.prototype[Et]=!0,H.prototype.removeEventListener=function(t,i,s,h){Gn(this,t,i,s,h)};function $(t,i){var s,h=t.G;if(h)for(s=[];h;h=h.G)s.push(h);if(t=t.M,h=i.type||i,typeof i=="string")i=new p(i,t);else if(i instanceof p)i.target=i.target||t;else{var y=i;i=new p(h,t),Hn(i,y)}y=!0;let w,E;if(s)for(E=s.length-1;E>=0;E--)w=i.g=s[E],y=we(w,h,!0,i)&&y;if(w=i.g=t,y=we(w,h,!0,i)&&y,y=we(w,h,!1,i)&&y,s)for(E=0;E<s.length;E++)w=i.g=s[E],y=we(w,h,!1,i)&&y}H.prototype.N=function(){if(H.Z.N.call(this),this.i){var t=this.i;for(const i in t.g){const s=t.g[i];for(let h=0;h<s.length;h++)me(s[h]);delete t.g[i],t.h--}}this.G=null},H.prototype.J=function(t,i,s,h){return this.i.add(String(t),i,!1,s,h)},H.prototype.K=function(t,i,s,h){return this.i.add(String(t),i,!0,s,h)};function we(t,i,s,h){if(i=t.i.g[String(i)],!i)return!0;i=i.concat();let y=!0;for(let w=0;w<i.length;++w){const E=i[w];if(E&&!E.da&&E.capture==s){const S=E.listener,x=E.ha||E.src;E.fa&&Ge(t.i,E),y=S.call(x,h)!==!1&&y}}return y&&!h.defaultPrevented}function es(t,i){if(typeof t!="function")if(t&&typeof t.handleEvent=="function")t=A(t.handleEvent,t);else throw Error("Invalid listener argument");return Number(i)>2147483647?-1:f.setTimeout(t,i||0)}function qn(t){t.g=es(()=>{t.g=null,t.i&&(t.i=!1,qn(t))},t.l);const i=t.h;t.h=null,t.m.apply(null,i)}class ns extends m{constructor(i,s){super(),this.m=i,this.l=s,this.h=null,this.i=!1,this.g=null}j(i){this.h=arguments,this.g?this.i=!0:qn(this)}N(){super.N(),this.g&&(f.clearTimeout(this.g),this.g=null,this.i=!1,this.h=null)}}function Gt(t){m.call(this),this.h=t,this.g={}}T(Gt,m);var Kn=[];function Jn(t){ye(t.g,function(i,s){this.g.hasOwnProperty(s)&&Ke(i)},t),t.g={}}Gt.prototype.N=function(){Gt.Z.N.call(this),Jn(this)},Gt.prototype.handleEvent=function(){throw Error("EventHandler.handleEvent not implemented")};var Ye=f.JSON.stringify,is=f.JSON.parse,rs=class{stringify(t){return f.JSON.stringify(t,void 0)}parse(t){return f.JSON.parse(t,void 0)}};function Xn(){}function ss(){}var Wt={OPEN:"a",hb:"b",ERROR:"c",tb:"d"};function Qe(){p.call(this,"d")}T(Qe,p);function Ze(){p.call(this,"c")}T(Ze,p);var Mt={},Yn=null;function tn(){return Yn=Yn||new H}Mt.Ia="serverreachability";function Qn(t){p.call(this,Mt.Ia,t)}T(Qn,p);function zt(t){const i=tn();$(i,new Qn(i))}Mt.STAT_EVENT="statevent";function Zn(t,i){p.call(this,Mt.STAT_EVENT,t),this.stat=i}T(Zn,p);function G(t){const i=tn();$(i,new Zn(i,t))}Mt.Ja="timingevent";function ti(t,i){p.call(this,Mt.Ja,t),this.size=i}T(ti,p);function qt(t,i){if(typeof t!="function")throw Error("Fn must not be null and must be a function");return f.setTimeout(function(){t()},i)}function Kt(){this.g=!0}Kt.prototype.ua=function(){this.g=!1};function os(t,i,s,h,y,w){t.info(function(){if(t.g)if(w){var E="",S=w.split("&");for(let k=0;k<S.length;k++){var x=S[k].split("=");if(x.length>1){const F=x[0];x=x[1];const tt=F.split("_");E=tt.length>=2&&tt[1]=="type"?E+(F+"="+x+"&"):E+(F+"=redacted&")}}}else E=null;else E=w;return"XMLHTTP REQ ("+h+") [attempt "+y+"]: "+i+`
`+s+`
`+E})}function as(t,i,s,h,y,w,E){t.info(function(){return"XMLHTTP RESP ("+h+") [ attempt "+y+"]: "+i+`
`+s+`
`+w+" "+E})}function Ut(t,i,s,h){t.info(function(){return"XMLHTTP TEXT ("+i+"): "+cs(t,s)+(h?" "+h:"")})}function hs(t,i){t.info(function(){return"TIMEOUT: "+i})}Kt.prototype.info=function(){};function cs(t,i){if(!t.g)return i;if(!i)return null;try{const w=JSON.parse(i);if(w){for(t=0;t<w.length;t++)if(Array.isArray(w[t])){var s=w[t];if(!(s.length<2)){var h=s[1];if(Array.isArray(h)&&!(h.length<1)){var y=h[0];if(y!="noop"&&y!="stop"&&y!="close")for(let E=1;E<h.length;E++)h[E]=""}}}}return Ye(w)}catch{return i}}var en={NO_ERROR:0,TIMEOUT:8},ls={},ei;function nn(){}T(nn,Xn),nn.prototype.g=function(){return new XMLHttpRequest},ei=new nn;function Jt(t){return encodeURIComponent(String(t))}function us(t){var i=1;t=t.split(":");const s=[];for(;i>0&&t.length;)s.push(t.shift()),i--;return t.length&&s.push(t.join(":")),s}function ut(t,i,s,h){this.j=t,this.i=i,this.l=s,this.S=h||1,this.V=new Gt(this),this.H=45e3,this.J=null,this.o=!1,this.u=this.B=this.A=this.M=this.F=this.T=this.D=null,this.G=[],this.g=null,this.C=0,this.m=this.v=null,this.X=-1,this.K=!1,this.P=0,this.O=null,this.W=this.L=this.U=this.R=!1,this.h=new ni}function ni(){this.i=null,this.g="",this.h=!1}var ii={},rn={};function sn(t,i,s){t.M=1,t.A=Ie(Z(i)),t.u=s,t.R=!0,ri(t,null)}function ri(t,i){t.F=Date.now(),ve(t),t.B=Z(t.A);var s=t.B,h=t.S;Array.isArray(h)||(h=[String(h)]),yi(s.i,"t",h),t.C=0,s=t.j.L,t.h=new ni,t.g=Mi(t.j,s?i:null,!t.u),t.P>0&&(t.O=new ns(A(t.Y,t,t.g),t.P)),i=t.V,s=t.g,h=t.ba;var y="readystatechange";Array.isArray(y)||(y&&(Kn[0]=y.toString()),y=Kn);for(let w=0;w<y.length;w++){const E=$n(s,y[w],h||i.handleEvent,!1,i.h||i);if(!E)break;i.g[E.key]=E}i=t.J?jn(t.J):{},t.u?(t.v||(t.v="POST"),i["Content-Type"]="application/x-www-form-urlencoded",t.g.ea(t.B,t.v,t.u,i)):(t.v="GET",t.g.ea(t.B,t.v,null,i)),zt(),os(t.i,t.v,t.B,t.l,t.S,t.u)}ut.prototype.ba=function(t){t=t.target;const i=this.O;i&&pt(t)==3?i.j():this.Y(t)},ut.prototype.Y=function(t){try{if(t==this.g)t:{const S=pt(this.g),x=this.g.ya(),k=this.g.ca();if(!(S<3)&&(S!=3||this.g&&(this.h.h||this.g.la()||Ti(this.g)))){this.K||S!=4||x==7||(x==8||k<=0?zt(3):zt(2)),on(this);var i=this.g.ca();this.X=i;var s=fs(this);if(this.o=i==200,as(this.i,this.v,this.B,this.l,this.S,S,i),this.o){if(this.U&&!this.L){e:{if(this.g){var h,y=this.g;if((h=y.g?y.g.getResponseHeader("X-HTTP-Initial-Response"):null)&&!l(h)){var w=h;break e}}w=null}if(t=w)Ut(this.i,this.l,t,"Initial handshake response via X-HTTP-Initial-Response"),this.L=!0,an(this,t);else{this.o=!1,this.m=3,G(12),At(this),Xt(this);break t}}if(this.R){t=!0;let F;for(;!this.K&&this.C<s.length;)if(F=ds(this,s),F==rn){S==4&&(this.m=4,G(14),t=!1),Ut(this.i,this.l,null,"[Incomplete Response]");break}else if(F==ii){this.m=4,G(15),Ut(this.i,this.l,s,"[Invalid Chunk]"),t=!1;break}else Ut(this.i,this.l,F,null),an(this,F);if(si(this)&&this.C!=0&&(this.h.g=this.h.g.slice(this.C),this.C=0),S!=4||s.length!=0||this.h.h||(this.m=1,G(16),t=!1),this.o=this.o&&t,!t)Ut(this.i,this.l,s,"[Invalid Chunked Response]"),At(this),Xt(this);else if(s.length>0&&!this.W){this.W=!0;var E=this.j;E.g==this&&E.aa&&!E.P&&(E.j.info("Great, no buffering proxy detected. Bytes received: "+s.length),gn(E),E.P=!0,G(11))}}else Ut(this.i,this.l,s,null),an(this,s);S==4&&At(this),this.o&&!this.K&&(S==4?Di(this.j,this):(this.o=!1,ve(this)))}else Cs(this.g),i==400&&s.indexOf("Unknown SID")>0?(this.m=3,G(12)):(this.m=0,G(13)),At(this),Xt(this)}}}catch{}finally{}};function fs(t){if(!si(t))return t.g.la();const i=Ti(t.g);if(i==="")return"";let s="";const h=i.length,y=pt(t.g)==4;if(!t.h.i){if(typeof TextDecoder>"u")return At(t),Xt(t),"";t.h.i=new f.TextDecoder}for(let w=0;w<h;w++)t.h.h=!0,s+=t.h.i.decode(i[w],{stream:!(y&&w==h-1)});return i.length=0,t.h.g+=s,t.C=0,t.h.g}function si(t){return t.g?t.v=="GET"&&t.M!=2&&t.j.Aa:!1}function ds(t,i){var s=t.C,h=i.indexOf(`
`,s);return h==-1?rn:(s=Number(i.substring(s,h)),isNaN(s)?ii:(h+=1,h+s>i.length?rn:(i=i.slice(h,h+s),t.C=h+s,i)))}ut.prototype.cancel=function(){this.K=!0,At(this)};function ve(t){t.T=Date.now()+t.H,oi(t,t.H)}function oi(t,i){if(t.D!=null)throw Error("WatchDog timer not null");t.D=qt(A(t.aa,t),i)}function on(t){t.D&&(f.clearTimeout(t.D),t.D=null)}ut.prototype.aa=function(){this.D=null;const t=Date.now();t-this.T>=0?(hs(this.i,this.B),this.M!=2&&(zt(),G(17)),At(this),this.m=2,Xt(this)):oi(this,this.T-t)};function Xt(t){t.j.I==0||t.K||Di(t.j,t)}function At(t){on(t);var i=t.O;i&&typeof i.dispose=="function"&&i.dispose(),t.O=null,Jn(t.V),t.g&&(i=t.g,t.g=null,i.abort(),i.dispose())}function an(t,i){try{var s=t.j;if(s.I!=0&&(s.g==t||hn(s.h,t))){if(!t.L&&hn(s.h,t)&&s.I==3){try{var h=s.Ba.g.parse(i)}catch{h=null}if(Array.isArray(h)&&h.length==3){var y=h;if(y[0]==0){t:if(!s.v){if(s.g)if(s.g.F+3e3<t.F)be(s),Te(s);else break t;pn(s),G(18)}}else s.xa=y[1],0<s.xa-s.K&&y[2]<37500&&s.F&&s.A==0&&!s.C&&(s.C=qt(A(s.Va,s),6e3));ci(s.h)<=1&&s.ta&&(s.ta=void 0)}else St(s,11)}else if((t.L||s.g==t)&&be(s),!l(i))for(y=s.Ba.g.parse(i),i=0;i<y.length;i++){let k=y[i];const F=k[0];if(!(F<=s.K))if(s.K=F,k=k[1],s.I==2)if(k[0]=="c"){s.M=k[1],s.ba=k[2];const tt=k[3];tt!=null&&(s.ka=tt,s.j.info("VER="+s.ka));const bt=k[4];bt!=null&&(s.za=bt,s.j.info("SVER="+s.za));const gt=k[5];gt!=null&&typeof gt=="number"&&gt>0&&(h=1.5*gt,s.O=h,s.j.info("backChannelRequestTimeoutMs_="+h)),h=s;const mt=t.g;if(mt){const Ce=mt.g?mt.g.getResponseHeader("X-Client-Wire-Protocol"):null;if(Ce){var w=h.h;w.g||Ce.indexOf("spdy")==-1&&Ce.indexOf("quic")==-1&&Ce.indexOf("h2")==-1||(w.j=w.l,w.g=new Set,w.h&&(cn(w,w.h),w.h=null))}if(h.G){const mn=mt.g?mt.g.getResponseHeader("X-HTTP-Session-Id"):null;mn&&(h.wa=mn,O(h.J,h.G,mn))}}s.I=3,s.l&&s.l.ra(),s.aa&&(s.T=Date.now()-t.F,s.j.info("Handshake RTT: "+s.T+"ms")),h=s;var E=t;if(h.na=Li(h,h.L?h.ba:null,h.W),E.L){li(h.h,E);var S=E,x=h.O;x&&(S.H=x),S.D&&(on(S),ve(S)),h.g=E}else Ni(h);s.i.length>0&&Se(s)}else k[0]!="stop"&&k[0]!="close"||St(s,7);else s.I==3&&(k[0]=="stop"||k[0]=="close"?k[0]=="stop"?St(s,7):dn(s):k[0]!="noop"&&s.l&&s.l.qa(k),s.A=0)}}zt(4)}catch{}}var ps=class{constructor(t,i){this.g=t,this.map=i}};function ai(t){this.l=t||10,f.PerformanceNavigationTiming?(t=f.performance.getEntriesByType("navigation"),t=t.length>0&&(t[0].nextHopProtocol=="hq"||t[0].nextHopProtocol=="h2")):t=!!(f.chrome&&f.chrome.loadTimes&&f.chrome.loadTimes()&&f.chrome.loadTimes().wasFetchedViaSpdy),this.j=t?this.l:1,this.g=null,this.j>1&&(this.g=new Set),this.h=null,this.i=[]}function hi(t){return t.h?!0:t.g?t.g.size>=t.j:!1}function ci(t){return t.h?1:t.g?t.g.size:0}function hn(t,i){return t.h?t.h==i:t.g?t.g.has(i):!1}function cn(t,i){t.g?t.g.add(i):t.h=i}function li(t,i){t.h&&t.h==i?t.h=null:t.g&&t.g.has(i)&&t.g.delete(i)}ai.prototype.cancel=function(){if(this.i=ui(this),this.h)this.h.cancel(),this.h=null;else if(this.g&&this.g.size!==0){for(const t of this.g.values())t.cancel();this.g.clear()}};function ui(t){if(t.h!=null)return t.i.concat(t.h.G);if(t.g!=null&&t.g.size!==0){let i=t.i;for(const s of t.g.values())i=i.concat(s.G);return i}return W(t.i)}var fi=RegExp("^(?:([^:/?#.]+):)?(?://(?:([^\\\\/?#]*)@)?([^\\\\/?#]*?)(?::([0-9]+))?(?=[\\\\/?#]|$))?([^?#]+)?(?:\\?([^#]*))?(?:#([\\s\\S]*))?$");function gs(t,i){if(t){t=t.split("&");for(let s=0;s<t.length;s++){const h=t[s].indexOf("=");let y,w=null;h>=0?(y=t[s].substring(0,h),w=t[s].substring(h+1)):y=t[s],i(y,w?decodeURIComponent(w.replace(/\+/g," ")):"")}}}function ft(t){this.g=this.o=this.j="",this.u=null,this.m=this.h="",this.l=!1;let i;t instanceof ft?(this.l=t.l,Yt(this,t.j),this.o=t.o,this.g=t.g,Qt(this,t.u),this.h=t.h,ln(this,_i(t.i)),this.m=t.m):t&&(i=String(t).match(fi))?(this.l=!1,Yt(this,i[1]||"",!0),this.o=Zt(i[2]||""),this.g=Zt(i[3]||"",!0),Qt(this,i[4]),this.h=Zt(i[5]||"",!0),ln(this,i[6]||"",!0),this.m=Zt(i[7]||"")):(this.l=!1,this.i=new ee(null,this.l))}ft.prototype.toString=function(){const t=[];var i=this.j;i&&t.push(te(i,di,!0),":");var s=this.g;return(s||i=="file")&&(t.push("//"),(i=this.o)&&t.push(te(i,di,!0),"@"),t.push(Jt(s).replace(/%25([0-9a-fA-F]{2})/g,"%$1")),s=this.u,s!=null&&t.push(":",String(s))),(s=this.h)&&(this.g&&s.charAt(0)!="/"&&t.push("/"),t.push(te(s,s.charAt(0)=="/"?_s:ys,!0))),(s=this.i.toString())&&t.push("?",s),(s=this.m)&&t.push("#",te(s,vs)),t.join("")},ft.prototype.resolve=function(t){const i=Z(this);let s=!!t.j;s?Yt(i,t.j):s=!!t.o,s?i.o=t.o:s=!!t.g,s?i.g=t.g:s=t.u!=null;var h=t.h;if(s)Qt(i,t.u);else if(s=!!t.h){if(h.charAt(0)!="/")if(this.g&&!this.h)h="/"+h;else{var y=i.h.lastIndexOf("/");y!=-1&&(h=i.h.slice(0,y+1)+h)}if(y=h,y==".."||y==".")h="";else if(y.indexOf("./")!=-1||y.indexOf("/.")!=-1){h=y.lastIndexOf("/",0)==0,y=y.split("/");const w=[];for(let E=0;E<y.length;){const S=y[E++];S=="."?h&&E==y.length&&w.push(""):S==".."?((w.length>1||w.length==1&&w[0]!="")&&w.pop(),h&&E==y.length&&w.push("")):(w.push(S),h=!0)}h=w.join("/")}else h=y}return s?i.h=h:s=t.i.toString()!=="",s?ln(i,_i(t.i)):s=!!t.m,s&&(i.m=t.m),i};function Z(t){return new ft(t)}function Yt(t,i,s){t.j=s?Zt(i,!0):i,t.j&&(t.j=t.j.replace(/:$/,""))}function Qt(t,i){if(i){if(i=Number(i),isNaN(i)||i<0)throw Error("Bad port number "+i);t.u=i}else t.u=null}function ln(t,i,s){i instanceof ee?(t.i=i,Is(t.i,t.l)):(s||(i=te(i,ws)),t.i=new ee(i,t.l))}function O(t,i,s){t.i.set(i,s)}function Ie(t){return O(t,"zx",Math.floor(Math.random()*2147483648).toString(36)+Math.abs(Math.floor(Math.random()*2147483648)^Date.now()).toString(36)),t}function Zt(t,i){return t?i?decodeURI(t.replace(/%25/g,"%2525")):decodeURIComponent(t):""}function te(t,i,s){return typeof t=="string"?(t=encodeURI(t).replace(i,ms),s&&(t=t.replace(/%25([0-9a-fA-F]{2})/g,"%$1")),t):null}function ms(t){return t=t.charCodeAt(0),"%"+(t>>4&15).toString(16)+(t&15).toString(16)}var di=/[#\/\?@]/g,ys=/[#\?:]/g,_s=/[#\?]/g,ws=/[#\?@]/g,vs=/#/g;function ee(t,i){this.h=this.g=null,this.i=t||null,this.j=!!i}function Tt(t){t.g||(t.g=new Map,t.h=0,t.i&&gs(t.i,function(i,s){t.add(decodeURIComponent(i.replace(/\+/g," ")),s)}))}r=ee.prototype,r.add=function(t,i){Tt(this),this.i=null,t=xt(this,t);let s=this.g.get(t);return s||this.g.set(t,s=[]),s.push(i),this.h+=1,this};function pi(t,i){Tt(t),i=xt(t,i),t.g.has(i)&&(t.i=null,t.h-=t.g.get(i).length,t.g.delete(i))}function gi(t,i){return Tt(t),i=xt(t,i),t.g.has(i)}r.forEach=function(t,i){Tt(this),this.g.forEach(function(s,h){s.forEach(function(y){t.call(i,y,h,this)},this)},this)};function mi(t,i){Tt(t);let s=[];if(typeof i=="string")gi(t,i)&&(s=s.concat(t.g.get(xt(t,i))));else for(t=Array.from(t.g.values()),i=0;i<t.length;i++)s=s.concat(t[i]);return s}r.set=function(t,i){return Tt(this),this.i=null,t=xt(this,t),gi(this,t)&&(this.h-=this.g.get(t).length),this.g.set(t,[i]),this.h+=1,this},r.get=function(t,i){return t?(t=mi(this,t),t.length>0?String(t[0]):i):i};function yi(t,i,s){pi(t,i),s.length>0&&(t.i=null,t.g.set(xt(t,i),W(s)),t.h+=s.length)}r.toString=function(){if(this.i)return this.i;if(!this.g)return"";const t=[],i=Array.from(this.g.keys());for(let h=0;h<i.length;h++){var s=i[h];const y=Jt(s);s=mi(this,s);for(let w=0;w<s.length;w++){let E=y;s[w]!==""&&(E+="="+Jt(s[w])),t.push(E)}}return this.i=t.join("&")};function _i(t){const i=new ee;return i.i=t.i,t.g&&(i.g=new Map(t.g),i.h=t.h),i}function xt(t,i){return i=String(i),t.j&&(i=i.toLowerCase()),i}function Is(t,i){i&&!t.j&&(Tt(t),t.i=null,t.g.forEach(function(s,h){const y=h.toLowerCase();h!=y&&(pi(this,h),yi(this,y,s))},t)),t.j=i}function Es(t,i){const s=new Kt;if(f.Image){const h=new Image;h.onload=D(dt,s,"TestLoadImage: loaded",!0,i,h),h.onerror=D(dt,s,"TestLoadImage: error",!1,i,h),h.onabort=D(dt,s,"TestLoadImage: abort",!1,i,h),h.ontimeout=D(dt,s,"TestLoadImage: timeout",!1,i,h),f.setTimeout(function(){h.ontimeout&&h.ontimeout()},1e4),h.src=t}else i(!1)}function As(t,i){const s=new Kt,h=new AbortController,y=setTimeout(()=>{h.abort(),dt(s,"TestPingServer: timeout",!1,i)},1e4);fetch(t,{signal:h.signal}).then(w=>{clearTimeout(y),w.ok?dt(s,"TestPingServer: ok",!0,i):dt(s,"TestPingServer: server error",!1,i)}).catch(()=>{clearTimeout(y),dt(s,"TestPingServer: error",!1,i)})}function dt(t,i,s,h,y){try{y&&(y.onload=null,y.onerror=null,y.onabort=null,y.ontimeout=null),h(s)}catch{}}function Ts(){this.g=new rs}function un(t){this.i=t.Sb||null,this.h=t.ab||!1}T(un,Xn),un.prototype.g=function(){return new Ee(this.i,this.h)};function Ee(t,i){H.call(this),this.H=t,this.o=i,this.m=void 0,this.status=this.readyState=0,this.responseType=this.responseText=this.response=this.statusText="",this.onreadystatechange=null,this.A=new Headers,this.h=null,this.F="GET",this.D="",this.g=!1,this.B=this.j=this.l=null,this.v=new AbortController}T(Ee,H),r=Ee.prototype,r.open=function(t,i){if(this.readyState!=0)throw this.abort(),Error("Error reopening a connection");this.F=t,this.D=i,this.readyState=1,ie(this)},r.send=function(t){if(this.readyState!=1)throw this.abort(),Error("need to call open() first. ");if(this.v.signal.aborted)throw this.abort(),Error("Request was aborted.");this.g=!0;const i={headers:this.A,method:this.F,credentials:this.m,cache:void 0,signal:this.v.signal};t&&(i.body=t),(this.H||f).fetch(new Request(this.D,i)).then(this.Pa.bind(this),this.ga.bind(this))},r.abort=function(){this.response=this.responseText="",this.A=new Headers,this.status=0,this.v.abort(),this.j&&this.j.cancel("Request was aborted.").catch(()=>{}),this.readyState>=1&&this.g&&this.readyState!=4&&(this.g=!1,ne(this)),this.readyState=0},r.Pa=function(t){if(this.g&&(this.l=t,this.h||(this.status=this.l.status,this.statusText=this.l.statusText,this.h=t.headers,this.readyState=2,ie(this)),this.g&&(this.readyState=3,ie(this),this.g)))if(this.responseType==="arraybuffer")t.arrayBuffer().then(this.Na.bind(this),this.ga.bind(this));else if(typeof f.ReadableStream<"u"&&"body"in t){if(this.j=t.body.getReader(),this.o){if(this.responseType)throw Error('responseType must be empty for "streamBinaryChunks" mode responses.');this.response=[]}else this.response=this.responseText="",this.B=new TextDecoder;wi(this)}else t.text().then(this.Oa.bind(this),this.ga.bind(this))};function wi(t){t.j.read().then(t.Ma.bind(t)).catch(t.ga.bind(t))}r.Ma=function(t){if(this.g){if(this.o&&t.value)this.response.push(t.value);else if(!this.o){var i=t.value?t.value:new Uint8Array(0);(i=this.B.decode(i,{stream:!t.done}))&&(this.response=this.responseText+=i)}t.done?ne(this):ie(this),this.readyState==3&&wi(this)}},r.Oa=function(t){this.g&&(this.response=this.responseText=t,ne(this))},r.Na=function(t){this.g&&(this.response=t,ne(this))},r.ga=function(){this.g&&ne(this)};function ne(t){t.readyState=4,t.l=null,t.j=null,t.B=null,ie(t)}r.setRequestHeader=function(t,i){this.A.append(t,i)},r.getResponseHeader=function(t){return this.h&&this.h.get(t.toLowerCase())||""},r.getAllResponseHeaders=function(){if(!this.h)return"";const t=[],i=this.h.entries();for(var s=i.next();!s.done;)s=s.value,t.push(s[0]+": "+s[1]),s=i.next();return t.join(`\r
`)};function ie(t){t.onreadystatechange&&t.onreadystatechange.call(t)}Object.defineProperty(Ee.prototype,"withCredentials",{get:function(){return this.m==="include"},set:function(t){this.m=t?"include":"same-origin"}});function vi(t){let i="";return ye(t,function(s,h){i+=h,i+=":",i+=s,i+=`\r
`}),i}function fn(t,i,s){t:{for(h in s){var h=!1;break t}h=!0}h||(s=vi(s),typeof t=="string"?s!=null&&Jt(s):O(t,i,s))}function M(t){H.call(this),this.headers=new Map,this.L=t||null,this.h=!1,this.g=null,this.D="",this.o=0,this.l="",this.j=this.B=this.v=this.A=!1,this.m=null,this.F="",this.H=!1}T(M,H);var Ss=/^https?$/i,bs=["POST","PUT"];r=M.prototype,r.Fa=function(t){this.H=t},r.ea=function(t,i,s,h){if(this.g)throw Error("[goog.net.XhrIo] Object is active with another request="+this.D+"; newUri="+t);i=i?i.toUpperCase():"GET",this.D=t,this.l="",this.o=0,this.A=!1,this.h=!0,this.g=this.L?this.L.g():ei.g(),this.g.onreadystatechange=B(A(this.Ca,this));try{this.B=!0,this.g.open(i,String(t),!0),this.B=!1}catch(w){Ii(this,w);return}if(t=s||"",s=new Map(this.headers),h)if(Object.getPrototypeOf(h)===Object.prototype)for(var y in h)s.set(y,h[y]);else if(typeof h.keys=="function"&&typeof h.get=="function")for(const w of h.keys())s.set(w,h.get(w));else throw Error("Unknown input type for opt_headers: "+String(h));h=Array.from(s.keys()).find(w=>w.toLowerCase()=="content-type"),y=f.FormData&&t instanceof f.FormData,!(Array.prototype.indexOf.call(bs,i,void 0)>=0)||h||y||s.set("Content-Type","application/x-www-form-urlencoded;charset=utf-8");for(const[w,E]of s)this.g.setRequestHeader(w,E);this.F&&(this.g.responseType=this.F),"withCredentials"in this.g&&this.g.withCredentials!==this.H&&(this.g.withCredentials=this.H);try{this.m&&(clearTimeout(this.m),this.m=null),this.v=!0,this.g.send(t),this.v=!1}catch(w){Ii(this,w)}};function Ii(t,i){t.h=!1,t.g&&(t.j=!0,t.g.abort(),t.j=!1),t.l=i,t.o=5,Ei(t),Ae(t)}function Ei(t){t.A||(t.A=!0,$(t,"complete"),$(t,"error"))}r.abort=function(t){this.g&&this.h&&(this.h=!1,this.j=!0,this.g.abort(),this.j=!1,this.o=t||7,$(this,"complete"),$(this,"abort"),Ae(this))},r.N=function(){this.g&&(this.h&&(this.h=!1,this.j=!0,this.g.abort(),this.j=!1),Ae(this,!0)),M.Z.N.call(this)},r.Ca=function(){this.u||(this.B||this.v||this.j?Ai(this):this.Xa())},r.Xa=function(){Ai(this)};function Ai(t){if(t.h&&typeof d<"u"){if(t.v&&pt(t)==4)setTimeout(t.Ca.bind(t),0);else if($(t,"readystatechange"),pt(t)==4){t.h=!1;try{const w=t.ca();t:switch(w){case 200:case 201:case 202:case 204:case 206:case 304:case 1223:var i=!0;break t;default:i=!1}var s;if(!(s=i)){var h;if(h=w===0){let E=String(t.D).match(fi)[1]||null;!E&&f.self&&f.self.location&&(E=f.self.location.protocol.slice(0,-1)),h=!Ss.test(E?E.toLowerCase():"")}s=h}if(s)$(t,"complete"),$(t,"success");else{t.o=6;try{var y=pt(t)>2?t.g.statusText:""}catch{y=""}t.l=y+" ["+t.ca()+"]",Ei(t)}}finally{Ae(t)}}}}function Ae(t,i){if(t.g){t.m&&(clearTimeout(t.m),t.m=null);const s=t.g;t.g=null,i||$(t,"ready");try{s.onreadystatechange=null}catch{}}}r.isActive=function(){return!!this.g};function pt(t){return t.g?t.g.readyState:0}r.ca=function(){try{return pt(this)>2?this.g.status:-1}catch{return-1}},r.la=function(){try{return this.g?this.g.responseText:""}catch{return""}},r.La=function(t){if(this.g){var i=this.g.responseText;return t&&i.indexOf(t)==0&&(i=i.substring(t.length)),is(i)}};function Ti(t){try{if(!t.g)return null;if("response"in t.g)return t.g.response;switch(t.F){case"":case"text":return t.g.responseText;case"arraybuffer":if("mozResponseArrayBuffer"in t.g)return t.g.mozResponseArrayBuffer}return null}catch{return null}}function Cs(t){const i={};t=(t.g&&pt(t)>=2&&t.g.getAllResponseHeaders()||"").split(`\r
`);for(let h=0;h<t.length;h++){if(l(t[h]))continue;var s=us(t[h]);const y=s[0];if(s=s[1],typeof s!="string")continue;s=s.trim();const w=i[y]||[];i[y]=w,w.push(s)}Yr(i,function(h){return h.join(", ")})}r.ya=function(){return this.o},r.Ha=function(){return typeof this.l=="string"?this.l:String(this.l)};function re(t,i,s){return s&&s.internalChannelParams&&s.internalChannelParams[t]||i}function Si(t){this.za=0,this.i=[],this.j=new Kt,this.ba=this.na=this.J=this.W=this.g=this.wa=this.G=this.H=this.u=this.U=this.o=null,this.Ya=this.V=0,this.Sa=re("failFast",!1,t),this.F=this.C=this.v=this.m=this.l=null,this.X=!0,this.xa=this.K=-1,this.Y=this.A=this.D=0,this.Qa=re("baseRetryDelayMs",5e3,t),this.Za=re("retryDelaySeedMs",1e4,t),this.Ta=re("forwardChannelMaxRetries",2,t),this.va=re("forwardChannelRequestTimeoutMs",2e4,t),this.ma=t&&t.xmlHttpFactory||void 0,this.Ua=t&&t.Rb||void 0,this.Aa=t&&t.useFetchStreams||!1,this.O=void 0,this.L=t&&t.supportsCrossDomainXhr||!1,this.M="",this.h=new ai(t&&t.concurrentRequestLimit),this.Ba=new Ts,this.S=t&&t.fastHandshake||!1,this.R=t&&t.encodeInitMessageHeaders||!1,this.S&&this.R&&(this.R=!1),this.Ra=t&&t.Pb||!1,t&&t.ua&&this.j.ua(),t&&t.forceLongPolling&&(this.X=!1),this.aa=!this.S&&this.X&&t&&t.detectBufferingProxy||!1,this.ia=void 0,t&&t.longPollingTimeout&&t.longPollingTimeout>0&&(this.ia=t.longPollingTimeout),this.ta=void 0,this.T=0,this.P=!1,this.ja=this.B=null}r=Si.prototype,r.ka=8,r.I=1,r.connect=function(t,i,s,h){G(0),this.W=t,this.H=i||{},s&&h!==void 0&&(this.H.OSID=s,this.H.OAID=h),this.F=this.X,this.J=Li(this,null,this.W),Se(this)};function dn(t){if(bi(t),t.I==3){var i=t.V++,s=Z(t.J);if(O(s,"SID",t.M),O(s,"RID",i),O(s,"TYPE","terminate"),se(t,s),i=new ut(t,t.j,i),i.M=2,i.A=Ie(Z(s)),s=!1,f.navigator&&f.navigator.sendBeacon)try{s=f.navigator.sendBeacon(i.A.toString(),"")}catch{}!s&&f.Image&&(new Image().src=i.A,s=!0),s||(i.g=Mi(i.j,null),i.g.ea(i.A)),i.F=Date.now(),ve(i)}Oi(t)}function Te(t){t.g&&(gn(t),t.g.cancel(),t.g=null)}function bi(t){Te(t),t.v&&(f.clearTimeout(t.v),t.v=null),be(t),t.h.cancel(),t.m&&(typeof t.m=="number"&&f.clearTimeout(t.m),t.m=null)}function Se(t){if(!hi(t.h)&&!t.m){t.m=!0;var i=t.Ea;lt||c(),K||(lt(),K=!0),g.add(i,t),t.D=0}}function Ps(t,i){return ci(t.h)>=t.h.j-(t.m?1:0)?!1:t.m?(t.i=i.G.concat(t.i),!0):t.I==1||t.I==2||t.D>=(t.Sa?0:t.Ta)?!1:(t.m=qt(A(t.Ea,t,i),ki(t,t.D)),t.D++,!0)}r.Ea=function(t){if(this.m)if(this.m=null,this.I==1){if(!t){this.V=Math.floor(Math.random()*1e5),t=this.V++;const y=new ut(this,this.j,t);let w=this.o;if(this.U&&(w?(w=jn(w),Hn(w,this.U)):w=this.U),this.u!==null||this.R||(y.J=w,w=null),this.S)t:{for(var i=0,s=0;s<this.i.length;s++){e:{var h=this.i[s];if("__data__"in h.map&&(h=h.map.__data__,typeof h=="string")){h=h.length;break e}h=void 0}if(h===void 0)break;if(i+=h,i>4096){i=s;break t}if(i===4096||s===this.i.length-1){i=s+1;break t}}i=1e3}else i=1e3;i=Pi(this,y,i),s=Z(this.J),O(s,"RID",t),O(s,"CVER",22),this.G&&O(s,"X-HTTP-Session-Id",this.G),se(this,s),w&&(this.R?i="headers="+Jt(vi(w))+"&"+i:this.u&&fn(s,this.u,w)),cn(this.h,y),this.Ra&&O(s,"TYPE","init"),this.S?(O(s,"$req",i),O(s,"SID","null"),y.U=!0,sn(y,s,null)):sn(y,s,i),this.I=2}}else this.I==3&&(t?Ci(this,t):this.i.length==0||hi(this.h)||Ci(this))};function Ci(t,i){var s;i?s=i.l:s=t.V++;const h=Z(t.J);O(h,"SID",t.M),O(h,"RID",s),O(h,"AID",t.K),se(t,h),t.u&&t.o&&fn(h,t.u,t.o),s=new ut(t,t.j,s,t.D+1),t.u===null&&(s.J=t.o),i&&(t.i=i.G.concat(t.i)),i=Pi(t,s,1e3),s.H=Math.round(t.va*.5)+Math.round(t.va*.5*Math.random()),cn(t.h,s),sn(s,h,i)}function se(t,i){t.H&&ye(t.H,function(s,h){O(i,h,s)}),t.l&&ye({},function(s,h){O(i,h,s)})}function Pi(t,i,s){s=Math.min(t.i.length,s);const h=t.l?A(t.l.Ka,t.l,t):null;t:{var y=t.i;let S=-1;for(;;){const x=["count="+s];S==-1?s>0?(S=y[0].g,x.push("ofs="+S)):S=0:x.push("ofs="+S);let k=!0;for(let F=0;F<s;F++){var w=y[F].g;const tt=y[F].map;if(w-=S,w<0)S=Math.max(0,y[F].g-100),k=!1;else try{w="req"+w+"_"||"";try{var E=tt instanceof Map?tt:Object.entries(tt);for(const[bt,gt]of E){let mt=gt;v(gt)&&(mt=Ye(gt)),x.push(w+bt+"="+encodeURIComponent(mt))}}catch(bt){throw x.push(w+"type="+encodeURIComponent("_badmap")),bt}}catch{h&&h(tt)}}if(k){E=x.join("&");break t}}E=void 0}return t=t.i.splice(0,s),i.G=t,E}function Ni(t){if(!t.g&&!t.v){t.Y=1;var i=t.Da;lt||c(),K||(lt(),K=!0),g.add(i,t),t.A=0}}function pn(t){return t.g||t.v||t.A>=3?!1:(t.Y++,t.v=qt(A(t.Da,t),ki(t,t.A)),t.A++,!0)}r.Da=function(){if(this.v=null,Ri(this),this.aa&&!(this.P||this.g==null||this.T<=0)){var t=4*this.T;this.j.info("BP detection timer enabled: "+t),this.B=qt(A(this.Wa,this),t)}},r.Wa=function(){this.B&&(this.B=null,this.j.info("BP detection timeout reached."),this.j.info("Buffering proxy detected and switch to long-polling!"),this.F=!1,this.P=!0,G(10),Te(this),Ri(this))};function gn(t){t.B!=null&&(f.clearTimeout(t.B),t.B=null)}function Ri(t){t.g=new ut(t,t.j,"rpc",t.Y),t.u===null&&(t.g.J=t.o),t.g.P=0;var i=Z(t.na);O(i,"RID","rpc"),O(i,"SID",t.M),O(i,"AID",t.K),O(i,"CI",t.F?"0":"1"),!t.F&&t.ia&&O(i,"TO",t.ia),O(i,"TYPE","xmlhttp"),se(t,i),t.u&&t.o&&fn(i,t.u,t.o),t.O&&(t.g.H=t.O);var s=t.g;t=t.ba,s.M=1,s.A=Ie(Z(i)),s.u=null,s.R=!0,ri(s,t)}r.Va=function(){this.C!=null&&(this.C=null,Te(this),pn(this),G(19))};function be(t){t.C!=null&&(f.clearTimeout(t.C),t.C=null)}function Di(t,i){var s=null;if(t.g==i){be(t),gn(t),t.g=null;var h=2}else if(hn(t.h,i))s=i.G,li(t.h,i),h=1;else return;if(t.I!=0){if(i.o)if(h==1){s=i.u?i.u.length:0,i=Date.now()-i.F;var y=t.D;h=tn(),$(h,new ti(h,s)),Se(t)}else Ni(t);else if(y=i.m,y==3||y==0&&i.X>0||!(h==1&&Ps(t,i)||h==2&&pn(t)))switch(s&&s.length>0&&(i=t.h,i.i=i.i.concat(s)),y){case 1:St(t,5);break;case 4:St(t,10);break;case 3:St(t,6);break;default:St(t,2)}}}function ki(t,i){let s=t.Qa+Math.floor(Math.random()*t.Za);return t.isActive()||(s*=2),s*i}function St(t,i){if(t.j.info("Error code "+i),i==2){var s=A(t.bb,t),h=t.Ua;const y=!h;h=new ft(h||"//www.google.com/images/cleardot.gif"),f.location&&f.location.protocol=="http"||Yt(h,"https"),Ie(h),y?Es(h.toString(),s):As(h.toString(),s)}else G(2);t.I=0,t.l&&t.l.pa(i),Oi(t),bi(t)}r.bb=function(t){t?(this.j.info("Successfully pinged google.com"),G(2)):(this.j.info("Failed to ping google.com"),G(1))};function Oi(t){if(t.I=0,t.ja=[],t.l){const i=ui(t.h);(i.length!=0||t.i.length!=0)&&(V(t.ja,i),V(t.ja,t.i),t.h.i.length=0,W(t.i),t.i.length=0),t.l.oa()}}function Li(t,i,s){var h=s instanceof ft?Z(s):new ft(s);if(h.g!="")i&&(h.g=i+"."+h.g),Qt(h,h.u);else{var y=f.location;h=y.protocol,i=i?i+"."+y.hostname:y.hostname,y=+y.port;const w=new ft(null);h&&Yt(w,h),i&&(w.g=i),y&&Qt(w,y),s&&(w.h=s),h=w}return s=t.G,i=t.wa,s&&i&&O(h,s,i),O(h,"VER",t.ka),se(t,h),h}function Mi(t,i,s){if(i&&!t.L)throw Error("Can't create secondary domain capable XhrIo object.");return i=t.Aa&&!t.ma?new M(new un({ab:s})):new M(t.ma),i.Fa(t.L),i}r.isActive=function(){return!!this.l&&this.l.isActive(this)};function Ui(){}r=Ui.prototype,r.ra=function(){},r.qa=function(){},r.pa=function(){},r.oa=function(){},r.isActive=function(){return!0},r.Ka=function(){};function J(t,i){H.call(this),this.g=new Si(i),this.l=t,this.h=i&&i.messageUrlParams||null,t=i&&i.messageHeaders||null,i&&i.clientProtocolHeaderRequired&&(t?t["X-Client-Protocol"]="webchannel":t={"X-Client-Protocol":"webchannel"}),this.g.o=t,t=i&&i.initMessageHeaders||null,i&&i.messageContentType&&(t?t["X-WebChannel-Content-Type"]=i.messageContentType:t={"X-WebChannel-Content-Type":i.messageContentType}),i&&i.sa&&(t?t["X-WebChannel-Client-Profile"]=i.sa:t={"X-WebChannel-Client-Profile":i.sa}),this.g.U=t,(t=i&&i.Qb)&&!l(t)&&(this.g.u=t),this.A=i&&i.supportsCrossDomainXhr||!1,this.v=i&&i.sendRawJson||!1,(i=i&&i.httpSessionIdParam)&&!l(i)&&(this.g.G=i,t=this.h,t!==null&&i in t&&(t=this.h,i in t&&delete t[i])),this.j=new Vt(this)}T(J,H),J.prototype.m=function(){this.g.l=this.j,this.A&&(this.g.L=!0),this.g.connect(this.l,this.h||void 0)},J.prototype.close=function(){dn(this.g)},J.prototype.o=function(t){var i=this.g;if(typeof t=="string"){var s={};s.__data__=t,t=s}else this.v&&(s={},s.__data__=Ye(t),t=s);i.i.push(new ps(i.Ya++,t)),i.I==3&&Se(i)},J.prototype.N=function(){this.g.l=null,delete this.j,dn(this.g),delete this.g,J.Z.N.call(this)};function xi(t){Qe.call(this),t.__headers__&&(this.headers=t.__headers__,this.statusCode=t.__status__,delete t.__headers__,delete t.__status__);var i=t.__sm__;if(i){t:{for(const s in i){t=s;break t}t=void 0}(this.i=t)&&(t=this.i,i=i!==null&&t in i?i[t]:void 0),this.data=i}else this.data=t}T(xi,Qe);function Vi(){Ze.call(this),this.status=1}T(Vi,Ze);function Vt(t){this.g=t}T(Vt,Ui),Vt.prototype.ra=function(){$(this.g,"a")},Vt.prototype.qa=function(t){$(this.g,new xi(t))},Vt.prototype.pa=function(t){$(this.g,new Vi)},Vt.prototype.oa=function(){$(this.g,"b")},J.prototype.send=J.prototype.o,J.prototype.open=J.prototype.m,J.prototype.close=J.prototype.close,en.NO_ERROR=0,en.TIMEOUT=8,en.HTTP_ERROR=6,ls.COMPLETE="complete",ss.EventType=Wt,Wt.OPEN="a",Wt.CLOSE="b",Wt.ERROR="c",Wt.MESSAGE="d",H.prototype.listen=H.prototype.J,M.prototype.listenOnce=M.prototype.K,M.prototype.getLastError=M.prototype.Ha,M.prototype.getLastErrorCode=M.prototype.ya,M.prototype.getStatus=M.prototype.ca,M.prototype.getResponseJson=M.prototype.La,M.prototype.getResponseText=M.prototype.la,M.prototype.send=M.prototype.ea,M.prototype.setWithCredentials=M.prototype.Fa}).apply(typeof Ne<"u"?Ne:typeof self<"u"?self:typeof window<"u"?window:{});/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class q{constructor(e){this.uid=e}isAuthenticated(){return this.uid!=null}toKey(){return this.isAuthenticated()?"uid:"+this.uid:"anonymous-user"}isEqual(e){return e.uid===this.uid}}q.UNAUTHENTICATED=new q(null),q.GOOGLE_CREDENTIALS=new q("google-credentials-uid"),q.FIRST_PARTY=new q("first-party-uid"),q.MOCK_USER=new q("mock-user");/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */let $e="12.13.0";function ja(r){$e=r}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *//**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const Ve=new kn("@firebase/firestore");function Y(r,...e){if(Ve.logLevel<=R.DEBUG){const n=e.map(Gr);Ve.debug(`Firestore (${$e}): ${r}`,...n)}}function $r(r,...e){if(Ve.logLevel<=R.ERROR){const n=e.map(Gr);Ve.error(`Firestore (${$e}): ${r}`,...n)}}function Gr(r){if(typeof r=="string")return r;try{return(function(n){return JSON.stringify(n)})(r)}catch{return r}}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function Fe(r,e,n){let o="Unexpected state";typeof e=="string"?o=e:n=e,Wr(r,o,n)}function Wr(r,e,n){let o=`FIRESTORE (${$e}) INTERNAL ASSERTION FAILED: ${e} (ID: ${r.toString(16)})`;if(n!==void 0)try{o+=" CONTEXT: "+JSON.stringify(n)}catch{o+=" CONTEXT: "+n}throw $r(o),new Error(o)}function he(r,e,n,o){let a="Unexpected state";typeof n=="string"?a=n:o=n,r||Wr(e,a,o)}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const P={CANCELLED:"cancelled",INVALID_ARGUMENT:"invalid-argument",FAILED_PRECONDITION:"failed-precondition"};class N extends It{constructor(e,n){super(e,n),this.code=e,this.message=n,this.toString=()=>`${this.name}: [code=${this.code}]: ${this.message}`}}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class ce{constructor(){this.promise=new Promise(((e,n)=>{this.resolve=e,this.reject=n}))}}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Ba{constructor(e,n){this.user=n,this.type="OAuth",this.headers=new Map,this.headers.set("Authorization",`Bearer ${e}`)}}class Ha{getToken(){return Promise.resolve(null)}invalidateToken(){}start(e,n){e.enqueueRetryable((()=>n(q.UNAUTHENTICATED)))}shutdown(){}}class $a{constructor(e){this.t=e,this.currentUser=q.UNAUTHENTICATED,this.i=0,this.forceRefresh=!1,this.auth=null}start(e,n){he(this.o===void 0,42304);let o=this.i;const a=I=>this.i!==o?(o=this.i,n(I)):Promise.resolve();let d=new ce;this.o=()=>{this.i++,this.currentUser=this.u(),d.resolve(),d=new ce,e.enqueueRetryable((()=>a(this.currentUser)))};const f=()=>{const I=d;e.enqueueRetryable((async()=>{await I.promise,await a(this.currentUser)}))},v=I=>{Y("FirebaseAuthCredentialsProvider","Auth detected"),this.auth=I,this.o&&(this.auth.addAuthTokenListener(this.o),f())};this.t.onInit((I=>v(I))),setTimeout((()=>{if(!this.auth){const I=this.t.getImmediate({optional:!0});I?v(I):(Y("FirebaseAuthCredentialsProvider","Auth not yet detected"),d.resolve(),d=new ce)}}),0),f()}getToken(){const e=this.i,n=this.forceRefresh;return this.forceRefresh=!1,this.auth?this.auth.getToken(n).then((o=>this.i!==e?(Y("FirebaseAuthCredentialsProvider","getToken aborted due to token change."),this.getToken()):o?(he(typeof o.accessToken=="string",31837,{l:o}),new Ba(o.accessToken,this.currentUser)):null)):Promise.resolve(null)}invalidateToken(){this.forceRefresh=!0}shutdown(){this.auth&&this.o&&this.auth.removeAuthTokenListener(this.o),this.o=void 0}u(){const e=this.auth&&this.auth.getUid();return he(e===null||typeof e=="string",2055,{h:e}),new q(e)}}class Ga{constructor(e,n,o){this.P=e,this.T=n,this.I=o,this.type="FirstParty",this.user=q.FIRST_PARTY,this.R=new Map}A(){return this.I?this.I():null}get headers(){this.R.set("X-Goog-AuthUser",this.P);const e=this.A();return e&&this.R.set("Authorization",e),this.T&&this.R.set("X-Goog-Iam-Authorization-Token",this.T),this.R}}class Wa{constructor(e,n,o){this.P=e,this.T=n,this.I=o}getToken(){return Promise.resolve(new Ga(this.P,this.T,this.I))}start(e,n){e.enqueueRetryable((()=>n(q.FIRST_PARTY)))}shutdown(){}invalidateToken(){}}class sr{constructor(e){this.value=e,this.type="AppCheck",this.headers=new Map,e&&e.length>0&&this.headers.set("x-firebase-appcheck",this.value)}}class za{constructor(e,n){this.V=n,this.forceRefresh=!1,this.appCheck=null,this.m=null,this.p=null,Ct(e)&&e.settings.appCheckToken&&(this.p=e.settings.appCheckToken)}start(e,n){he(this.o===void 0,3512);const o=d=>{d.error!=null&&Y("FirebaseAppCheckTokenProvider",`Error getting App Check token; using placeholder token instead. Error: ${d.error.message}`);const f=d.token!==this.m;return this.m=d.token,Y("FirebaseAppCheckTokenProvider",`Received ${f?"new":"existing"} token.`),f?n(d.token):Promise.resolve()};this.o=d=>{e.enqueueRetryable((()=>o(d)))};const a=d=>{Y("FirebaseAppCheckTokenProvider","AppCheck detected"),this.appCheck=d,this.o&&this.appCheck.addTokenListener(this.o)};this.V.onInit((d=>a(d))),setTimeout((()=>{if(!this.appCheck){const d=this.V.getImmediate({optional:!0});d?a(d):Y("FirebaseAppCheckTokenProvider","AppCheck not yet detected")}}),0)}getToken(){if(this.p)return Promise.resolve(new sr(this.p));const e=this.forceRefresh;return this.forceRefresh=!1,this.appCheck?this.appCheck.getToken(e).then((n=>n?(he(typeof n.token=="string",44558,{tokenResult:n}),this.m=n.token,new sr(n.token)):null)):Promise.resolve(null)}invalidateToken(){this.forceRefresh=!0}shutdown(){this.appCheck&&this.o&&this.appCheck.removeTokenListener(this.o),this.o=void 0}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function qa(r){const e=typeof self<"u"&&(self.crypto||self.msCrypto),n=new Uint8Array(r);if(e&&typeof e.getRandomValues=="function")e.getRandomValues(n);else for(let o=0;o<r;o++)n[o]=Math.floor(256*Math.random());return n}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Ka{static newId(){const e="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",n=62*Math.floor(4.129032258064516);let o="";for(;o.length<20;){const a=qa(40);for(let d=0;d<a.length;++d)o.length<20&&a[d]<n&&(o+=e.charAt(a[d]%62))}return o}}function vt(r,e){return r<e?-1:r>e?1:0}function Ja(r,e){const n=Math.min(r.length,e.length);for(let o=0;o<n;o++){const a=r.charAt(o),d=e.charAt(o);if(a!==d)return Tn(a)===Tn(d)?vt(a,d):Tn(a)?1:-1}return vt(r.length,e.length)}const Xa=55296,Ya=57343;function Tn(r){const e=r.charCodeAt(0);return e>=Xa&&e<=Ya}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const or="__name__";class et{constructor(e,n,o){n===void 0?n=0:n>e.length&&Fe(637,{offset:n,range:e.length}),o===void 0?o=e.length-n:o>e.length-n&&Fe(1746,{length:o,range:e.length-n}),this.segments=e,this.offset=n,this.len=o}get length(){return this.len}isEqual(e){return et.comparator(this,e)===0}child(e){const n=this.segments.slice(this.offset,this.limit());return e instanceof et?e.forEach((o=>{n.push(o)})):n.push(e),this.construct(n)}limit(){return this.offset+this.length}popFirst(e){return e=e===void 0?1:e,this.construct(this.segments,this.offset+e,this.length-e)}popLast(){return this.construct(this.segments,this.offset,this.length-1)}firstSegment(){return this.segments[this.offset]}lastSegment(){return this.get(this.length-1)}get(e){return this.segments[this.offset+e]}isEmpty(){return this.length===0}isPrefixOf(e){if(e.length<this.length)return!1;for(let n=0;n<this.length;n++)if(this.get(n)!==e.get(n))return!1;return!0}isImmediateParentOf(e){if(this.length+1!==e.length)return!1;for(let n=0;n<this.length;n++)if(this.get(n)!==e.get(n))return!1;return!0}forEach(e){for(let n=this.offset,o=this.limit();n<o;n++)e(this.segments[n])}toArray(){return this.segments.slice(this.offset,this.limit())}static comparator(e,n){const o=Math.min(e.length,n.length);for(let a=0;a<o;a++){const d=et.compareSegments(e.get(a),n.get(a));if(d!==0)return d}return vt(e.length,n.length)}static compareSegments(e,n){const o=et.isNumericId(e),a=et.isNumericId(n);return o&&!a?-1:!o&&a?1:o&&a?et.extractNumericId(e).compare(et.extractNumericId(n)):Ja(e,n)}static isNumericId(e){return e.startsWith("__id")&&e.endsWith("__")}static extractNumericId(e){return Un.fromString(e.substring(4,e.length-2))}}class X extends et{construct(e,n,o){return new X(e,n,o)}canonicalString(){return this.toArray().join("/")}toString(){return this.canonicalString()}toUriEncodedString(){return this.toArray().map(encodeURIComponent).join("/")}static fromString(...e){const n=[];for(const o of e){if(o.indexOf("//")>=0)throw new N(P.INVALID_ARGUMENT,`Invalid segment (${o}). Paths must not contain // in them.`);n.push(...o.split("/").filter((a=>a.length>0)))}return new X(n)}static emptyPath(){return new X([])}}const Qa=/^[_a-zA-Z][_a-zA-Z0-9]*$/;class Pt extends et{construct(e,n,o){return new Pt(e,n,o)}static isValidIdentifier(e){return Qa.test(e)}canonicalString(){return this.toArray().map((e=>(e=e.replace(/\\/g,"\\\\").replace(/`/g,"\\`"),Pt.isValidIdentifier(e)||(e="`"+e+"`"),e))).join(".")}toString(){return this.canonicalString()}isKeyField(){return this.length===1&&this.get(0)===or}static keyField(){return new Pt([or])}static fromServerFormat(e){const n=[];let o="",a=0;const d=()=>{if(o.length===0)throw new N(P.INVALID_ARGUMENT,`Invalid field path (${e}). Paths must not be empty, begin with '.', end with '.', or contain '..'`);n.push(o),o=""};let f=!1;for(;a<e.length;){const v=e[a];if(v==="\\"){if(a+1===e.length)throw new N(P.INVALID_ARGUMENT,"Path has trailing escape character: "+e);const I=e[a+1];if(I!=="\\"&&I!=="."&&I!=="`")throw new N(P.INVALID_ARGUMENT,"Path has invalid escape sequence: "+e);o+=I,a+=2}else v==="`"?(f=!f,a++):v!=="."||f?(o+=v,a++):(d(),a++)}if(d(),f)throw new N(P.INVALID_ARGUMENT,"Unterminated ` in path: "+e);return new Pt(n)}static emptyPath(){return new Pt([])}}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Rt{constructor(e){this.path=e}static fromPath(e){return new Rt(X.fromString(e))}static fromName(e){return new Rt(X.fromString(e).popFirst(5))}static empty(){return new Rt(X.emptyPath())}get collectionGroup(){return this.path.popLast().lastSegment()}hasCollectionId(e){return this.path.length>=2&&this.path.get(this.path.length-2)===e}getCollectionGroup(){return this.path.get(this.path.length-2)}getCollectionPath(){return this.path.popLast()}isEqual(e){return e!==null&&X.comparator(this.path,e.path)===0}toString(){return this.path.toString()}static comparator(e,n){return X.comparator(e.path,n.path)}static isDocumentKey(e){return e.length%2==0}static fromSegments(e){return new Rt(new X(e.slice()))}}function Za(r,e,n,o){if(e===!0&&o===!0)throw new N(P.INVALID_ARGUMENT,`${r} and ${n} cannot be used together.`)}function th(r){return typeof r=="object"&&r!==null&&(Object.getPrototypeOf(r)===Object.prototype||Object.getPrototypeOf(r)===null)}/**
 * @license
 * Copyright 2025 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function U(r,e){const n={typeString:r};return e&&(n.value=e),n}function ge(r,e){if(!th(r))throw new N(P.INVALID_ARGUMENT,"JSON must be an object");let n;for(const o in e)if(e[o]){const a=e[o].typeString,d="value"in e[o]?{value:e[o].value}:void 0;if(!(o in r)){n=`JSON missing required field: '${o}'`;break}const f=r[o];if(a&&typeof f!==a){n=`JSON field '${o}' must be a ${a}.`;break}if(d!==void 0&&f!==d.value){n=`Expected '${o}' field to equal '${d.value}'`;break}}if(n)throw new N(P.INVALID_ARGUMENT,n);return!0}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const ar=-62135596800,hr=1e6;class nt{static now(){return nt.fromMillis(Date.now())}static fromDate(e){return nt.fromMillis(e.getTime())}static fromMillis(e){const n=Math.floor(e/1e3),o=Math.floor((e-1e3*n)*hr);return new nt(n,o)}constructor(e,n){if(this.seconds=e,this.nanoseconds=n,n<0)throw new N(P.INVALID_ARGUMENT,"Timestamp nanoseconds out of range: "+n);if(n>=1e9)throw new N(P.INVALID_ARGUMENT,"Timestamp nanoseconds out of range: "+n);if(e<ar)throw new N(P.INVALID_ARGUMENT,"Timestamp seconds out of range: "+e);if(e>=253402300800)throw new N(P.INVALID_ARGUMENT,"Timestamp seconds out of range: "+e)}toDate(){return new Date(this.toMillis())}toMillis(){return 1e3*this.seconds+this.nanoseconds/hr}_compareTo(e){return this.seconds===e.seconds?vt(this.nanoseconds,e.nanoseconds):vt(this.seconds,e.seconds)}isEqual(e){return e.seconds===this.seconds&&e.nanoseconds===this.nanoseconds}toString(){return"Timestamp(seconds="+this.seconds+", nanoseconds="+this.nanoseconds+")"}toJSON(){return{type:nt._jsonSchemaVersion,seconds:this.seconds,nanoseconds:this.nanoseconds}}static fromJSON(e){if(ge(e,nt._jsonSchema))return new nt(e.seconds,e.nanoseconds)}valueOf(){const e=this.seconds-ar;return String(e).padStart(12,"0")+"."+String(this.nanoseconds).padStart(9,"0")}}nt._jsonSchemaVersion="firestore/timestamp/1.0",nt._jsonSchema={type:U("string",nt._jsonSchemaVersion),seconds:U("number"),nanoseconds:U("number")};function eh(r){return r.name==="IndexedDbTransactionError"}/**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class nh extends Error{constructor(){super(...arguments),this.name="Base64DecodeError"}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Ot{constructor(e){this.binaryString=e}static fromBase64String(e){const n=(function(a){try{return atob(a)}catch(d){throw typeof DOMException<"u"&&d instanceof DOMException?new nh("Invalid base64 string: "+d):d}})(e);return new Ot(n)}static fromUint8Array(e){const n=(function(a){let d="";for(let f=0;f<a.length;++f)d+=String.fromCharCode(a[f]);return d})(e);return new Ot(n)}[Symbol.iterator](){let e=0;return{next:()=>e<this.binaryString.length?{value:this.binaryString.charCodeAt(e++),done:!1}:{value:void 0,done:!0}}}toBase64(){return(function(n){return btoa(n)})(this.binaryString)}toUint8Array(){return(function(n){const o=new Uint8Array(n.length);for(let a=0;a<n.length;a++)o[a]=n.charCodeAt(a);return o})(this.binaryString)}approximateByteSize(){return 2*this.binaryString.length}compareTo(e){return vt(this.binaryString,e.binaryString)}isEqual(e){return this.binaryString===e.binaryString}}Ot.EMPTY_BYTE_STRING=new Ot("");const cr="(default)";class je{constructor(e,n){this.projectId=e,this.database=n||cr}static empty(){return new je("","")}get isDefaultDatabase(){return this.database===cr}isEqual(e){return e instanceof je&&e.projectId===this.projectId&&e.database===this.database}}function ih(r,e){if(!Object.prototype.hasOwnProperty.apply(r.options,["projectId"]))throw new N(P.INVALID_ARGUMENT,'"projectId" not provided in firebase.initializeApp.');return new je(r.options.projectId,e)}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class rh{constructor(e,n=null,o=[],a=[],d=null,f="F",v=null,I=null){this.path=e,this.collectionGroup=n,this.explicitOrderBy=o,this.filters=a,this.limit=d,this.limitType=f,this.startAt=v,this.endAt=I,this.Ie=null,this.Ee=null,this.Re=null,this.startAt,this.endAt}}function sh(r){return new rh(r)}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */var lr,b;(b=lr||(lr={}))[b.OK=0]="OK",b[b.CANCELLED=1]="CANCELLED",b[b.UNKNOWN=2]="UNKNOWN",b[b.INVALID_ARGUMENT=3]="INVALID_ARGUMENT",b[b.DEADLINE_EXCEEDED=4]="DEADLINE_EXCEEDED",b[b.NOT_FOUND=5]="NOT_FOUND",b[b.ALREADY_EXISTS=6]="ALREADY_EXISTS",b[b.PERMISSION_DENIED=7]="PERMISSION_DENIED",b[b.UNAUTHENTICATED=16]="UNAUTHENTICATED",b[b.RESOURCE_EXHAUSTED=8]="RESOURCE_EXHAUSTED",b[b.FAILED_PRECONDITION=9]="FAILED_PRECONDITION",b[b.ABORTED=10]="ABORTED",b[b.OUT_OF_RANGE=11]="OUT_OF_RANGE",b[b.UNIMPLEMENTED=12]="UNIMPLEMENTED",b[b.INTERNAL=13]="INTERNAL",b[b.UNAVAILABLE=14]="UNAVAILABLE",b[b.DATA_LOSS=15]="DATA_LOSS";/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */new Un([4294967295,4294967295],0);/**
 * @license
 * Copyright 2018 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const oh=41943040;/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const ah=1048576;function Sn(){return typeof document<"u"?document:null}class hh{constructor(e,n,o=1e3,a=1.5,d=6e4){this.Ci=e,this.timerId=n,this.R_=o,this.A_=a,this.V_=d,this.d_=0,this.m_=null,this.f_=Date.now(),this.reset()}reset(){this.d_=0}g_(){this.d_=this.V_}p_(e){this.cancel();const n=Math.floor(this.d_+this.y_()),o=Math.max(0,Date.now()-this.f_),a=Math.max(0,n-o);a>0&&Y("ExponentialBackoff",`Backing off for ${a} ms (base delay: ${this.d_} ms, delay with jitter: ${n} ms, last attempt: ${o} ms ago)`),this.m_=this.Ci.enqueueAfterDelay(this.timerId,a,(()=>(this.f_=Date.now(),e()))),this.d_*=this.A_,this.d_<this.R_&&(this.d_=this.R_),this.d_>this.V_&&(this.d_=this.V_)}w_(){this.m_!==null&&(this.m_.skipDelay(),this.m_=null)}cancel(){this.m_!==null&&(this.m_.cancel(),this.m_=null)}y_(){return(Math.random()-.5)*this.d_}}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class xn{constructor(e,n,o,a,d){this.asyncQueue=e,this.timerId=n,this.targetTimeMs=o,this.op=a,this.removalCallback=d,this.deferred=new ce,this.then=this.deferred.promise.then.bind(this.deferred.promise),this.deferred.promise.catch((f=>{}))}get promise(){return this.deferred.promise}static createAndSchedule(e,n,o,a,d){const f=Date.now()+o,v=new xn(e,n,f,a,d);return v.start(o),v}start(e){this.timerHandle=setTimeout((()=>this.handleDelayElapsed()),e)}skipDelay(){return this.handleDelayElapsed()}cancel(e){this.timerHandle!==null&&(this.clearTimeout(),this.deferred.reject(new N(P.CANCELLED,"Operation cancelled"+(e?": "+e:""))))}handleDelayElapsed(){this.asyncQueue.enqueueAndForget((()=>this.timerHandle!==null?(this.clearTimeout(),this.op().then((e=>this.deferred.resolve(e)))):Promise.resolve()))}clearTimeout(){this.timerHandle!==null&&(this.removalCallback(this),clearTimeout(this.timerHandle),this.timerHandle=null)}}var ur,fr;(fr=ur||(ur={})).Ba="default",fr.Cache="cache";/**
 * @license
 * Copyright 2023 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */function ch(r){const e={};return r.timeoutSeconds!==void 0&&(e.timeoutSeconds=r.timeoutSeconds),e}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const lh="ComponentProvider",dr=new Map;/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const uh="firestore.googleapis.com",pr=!0;class gr{constructor(e){if(e.host===void 0){if(e.ssl!==void 0)throw new N(P.INVALID_ARGUMENT,"Can't provide ssl option if host option is not set");this.host=uh,this.ssl=pr}else this.host=e.host,this.ssl=e.ssl??pr;if(this.isUsingEmulator=e.emulatorOptions!==void 0,this.credentials=e.credentials,this.ignoreUndefinedProperties=!!e.ignoreUndefinedProperties,this.localCache=e.localCache,e.cacheSizeBytes===void 0)this.cacheSizeBytes=oh;else{if(e.cacheSizeBytes!==-1&&e.cacheSizeBytes<ah)throw new N(P.INVALID_ARGUMENT,"cacheSizeBytes must be at least 1048576");this.cacheSizeBytes=e.cacheSizeBytes}Za("experimentalForceLongPolling",e.experimentalForceLongPolling,"experimentalAutoDetectLongPolling",e.experimentalAutoDetectLongPolling),this.experimentalForceLongPolling=!!e.experimentalForceLongPolling,this.experimentalForceLongPolling?this.experimentalAutoDetectLongPolling=!1:e.experimentalAutoDetectLongPolling===void 0?this.experimentalAutoDetectLongPolling=!0:this.experimentalAutoDetectLongPolling=!!e.experimentalAutoDetectLongPolling,this.experimentalLongPollingOptions=ch(e.experimentalLongPollingOptions??{}),(function(o){if(o.timeoutSeconds!==void 0){if(isNaN(o.timeoutSeconds))throw new N(P.INVALID_ARGUMENT,`invalid long polling timeout: ${o.timeoutSeconds} (must not be NaN)`);if(o.timeoutSeconds<5)throw new N(P.INVALID_ARGUMENT,`invalid long polling timeout: ${o.timeoutSeconds} (minimum allowed value is 5)`);if(o.timeoutSeconds>30)throw new N(P.INVALID_ARGUMENT,`invalid long polling timeout: ${o.timeoutSeconds} (maximum allowed value is 30)`)}})(this.experimentalLongPollingOptions),this.useFetchStreams=!!e.useFetchStreams}isEqual(e){return this.host===e.host&&this.ssl===e.ssl&&this.credentials===e.credentials&&this.cacheSizeBytes===e.cacheSizeBytes&&this.experimentalForceLongPolling===e.experimentalForceLongPolling&&this.experimentalAutoDetectLongPolling===e.experimentalAutoDetectLongPolling&&(function(o,a){return o.timeoutSeconds===a.timeoutSeconds})(this.experimentalLongPollingOptions,e.experimentalLongPollingOptions)&&this.ignoreUndefinedProperties===e.ignoreUndefinedProperties&&this.useFetchStreams===e.useFetchStreams}}class fh{constructor(e,n,o,a){this._authCredentials=e,this._appCheckCredentials=n,this._databaseId=o,this._app=a,this.type="firestore-lite",this._persistenceKey="(lite)",this._settings=new gr({}),this._settingsFrozen=!1,this._emulatorOptions={},this._terminateTask="notTerminated"}get app(){if(!this._app)throw new N(P.FAILED_PRECONDITION,"Firestore was not initialized using the Firebase SDK. 'app' is not available");return this._app}get _initialized(){return this._settingsFrozen}get _terminated(){return this._terminateTask!=="notTerminated"}_setSettings(e){if(this._settingsFrozen)throw new N(P.FAILED_PRECONDITION,"Firestore has already been started and its settings can no longer be changed. You can only modify settings before calling any other methods on a Firestore object.");this._settings=new gr(e),this._emulatorOptions=e.emulatorOptions||{},e.credentials!==void 0&&(this._authCredentials=(function(o){if(!o)return new Ha;switch(o.type){case"firstParty":return new Wa(o.sessionIndex||"0",o.iamToken||null,o.authTokenFactory||null);case"provider":return o.client;default:throw new N(P.INVALID_ARGUMENT,"makeAuthCredentialsProvider failed due to invalid credential type")}})(e.credentials))}_getSettings(){return this._settings}_getEmulatorOptions(){return this._emulatorOptions}_freezeSettings(){return this._settingsFrozen=!0,this._settings}_delete(){return this._terminateTask==="notTerminated"&&(this._terminateTask=this._terminate()),this._terminateTask}async _restart(){this._terminateTask==="notTerminated"?await this._terminate():this._terminateTask="notTerminated"}toJSON(){return{app:this._app,databaseId:this._databaseId,settings:this._settings}}_terminate(){return(function(n){const o=dr.get(n);o&&(Y(lh,"Removing Datastore"),dr.delete(n),o.terminate())})(this),Promise.resolve()}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Vn{constructor(e,n,o){this.converter=n,this._query=o,this.type="query",this.firestore=e}withConverter(e){return new Vn(this.firestore,e,this._query)}}class rt{constructor(e,n,o){this.converter=n,this._key=o,this.type="document",this.firestore=e}get _path(){return this._key.path}get id(){return this._key.path.lastSegment()}get path(){return this._key.path.canonicalString()}get parent(){return new Fn(this.firestore,this.converter,this._key.path.popLast())}withConverter(e){return new rt(this.firestore,e,this._key)}toJSON(){return{type:rt._jsonSchemaVersion,referencePath:this._key.toString()}}static fromJSON(e,n,o){if(ge(n,rt._jsonSchema))return new rt(e,o||null,new Rt(X.fromString(n.referencePath)))}}rt._jsonSchemaVersion="firestore/documentReference/1.0",rt._jsonSchema={type:U("string",rt._jsonSchemaVersion),referencePath:U("string")};class Fn extends Vn{constructor(e,n,o){super(e,n,sh(o)),this._path=o,this.type="collection"}get id(){return this._query.path.lastSegment()}get path(){return this._query.path.canonicalString()}get parent(){const e=this._path.popLast();return e.isEmpty()?null:new rt(this.firestore,null,new Rt(e))}withConverter(e){return new Fn(this.firestore,e,this._path)}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */const mr="AsyncQueue";class yr{constructor(e=Promise.resolve()){this.rc=[],this.sc=!1,this.oc=[],this._c=null,this.ac=!1,this.uc=!1,this.cc=[],this.M_=new hh(this,"async_queue_retry"),this.lc=()=>{const o=Sn();o&&Y(mr,"Visibility state changed to "+o.visibilityState),this.M_.w_()},this.hc=e;const n=Sn();n&&typeof n.addEventListener=="function"&&n.addEventListener("visibilitychange",this.lc)}get isShuttingDown(){return this.sc}enqueueAndForget(e){this.enqueue(e)}enqueueAndForgetEvenWhileRestricted(e){this.Pc(),this.Tc(e)}enterRestrictedMode(e){if(!this.sc){this.sc=!0,this.uc=e||!1;const n=Sn();n&&typeof n.removeEventListener=="function"&&n.removeEventListener("visibilitychange",this.lc)}}enqueue(e){if(this.Pc(),this.sc)return new Promise((()=>{}));const n=new ce;return this.Tc((()=>this.sc&&this.uc?Promise.resolve():(e().then(n.resolve,n.reject),n.promise))).then((()=>n.promise))}enqueueRetryable(e){this.enqueueAndForget((()=>(this.rc.push(e),this.Ic())))}async Ic(){if(this.rc.length!==0){try{await this.rc[0](),this.rc.shift(),this.M_.reset()}catch(e){if(!eh(e))throw e;Y(mr,"Operation failed with retryable error: "+e)}this.rc.length>0&&this.M_.p_((()=>this.Ic()))}}Tc(e){const n=this.hc.then((()=>(this.ac=!0,e().catch((o=>{throw this._c=o,this.ac=!1,$r("INTERNAL UNHANDLED ERROR: ",_r(o)),o})).then((o=>(this.ac=!1,o))))));return this.hc=n,n}enqueueAfterDelay(e,n,o){this.Pc(),this.cc.indexOf(e)>-1&&(n=0);const a=xn.createAndSchedule(this,e,n,o,(d=>this.Ec(d)));return this.oc.push(a),a}Pc(){this._c&&Fe(47125,{Rc:_r(this._c)})}verifyOperationInProgress(){}async Ac(){let e;do e=this.hc,await e;while(e!==this.hc)}Vc(e){for(const n of this.oc)if(n.timerId===e)return!0;return!1}dc(e){return this.Ac().then((()=>{this.oc.sort(((n,o)=>n.targetTimeMs-o.targetTimeMs));for(const n of this.oc)if(n.skipDelay(),e!=="all"&&n.timerId===e)break;return this.Ac()}))}mc(e){this.cc.push(e)}Ec(e){const n=this.oc.indexOf(e);this.oc.splice(n,1)}}function _r(r){let e=r.message||"";return r.stack&&(e=r.stack.includes(r.message)?r.stack:r.message+`
`+r.stack),e}class dh extends fh{constructor(e,n,o,a){super(e,n,o,a),this.type="firestore",this._queue=new yr,this._persistenceKey=(a==null?void 0:a.name)||"[DEFAULT]"}async _terminate(){if(this._firestoreClient){const e=this._firestoreClient.terminate();this._queue=new yr(e),this._firestoreClient=void 0,await e}}}/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class ot{constructor(e){this._byteString=e}static fromBase64String(e){try{return new ot(Ot.fromBase64String(e))}catch(n){throw new N(P.INVALID_ARGUMENT,"Failed to construct data from Base64 string: "+n)}}static fromUint8Array(e){return new ot(Ot.fromUint8Array(e))}toBase64(){return this._byteString.toBase64()}toUint8Array(){return this._byteString.toUint8Array()}toString(){return"Bytes(base64: "+this.toBase64()+")"}isEqual(e){return this._byteString.isEqual(e._byteString)}toJSON(){return{type:ot._jsonSchemaVersion,bytes:this.toBase64()}}static fromJSON(e){if(ge(e,ot._jsonSchema))return ot.fromBase64String(e.bytes)}}ot._jsonSchemaVersion="firestore/bytes/1.0",ot._jsonSchema={type:U("string",ot._jsonSchemaVersion),bytes:U("string")};/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class zr{constructor(...e){for(let n=0;n<e.length;++n)if(e[n].length===0)throw new N(P.INVALID_ARGUMENT,"Invalid field name at argument $(i + 1). Field names must not be empty.");this._internalPath=new Pt(e)}isEqual(e){return this._internalPath.isEqual(e._internalPath)}}/**
 * @license
 * Copyright 2017 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Dt{constructor(e,n){if(!isFinite(e)||e<-90||e>90)throw new N(P.INVALID_ARGUMENT,"Latitude must be a number between -90 and 90, but was: "+e);if(!isFinite(n)||n<-180||n>180)throw new N(P.INVALID_ARGUMENT,"Longitude must be a number between -180 and 180, but was: "+n);this._lat=e,this._long=n}get latitude(){return this._lat}get longitude(){return this._long}isEqual(e){return this._lat===e._lat&&this._long===e._long}_compareTo(e){return vt(this._lat,e._lat)||vt(this._long,e._long)}toJSON(){return{latitude:this._lat,longitude:this._long,type:Dt._jsonSchemaVersion}}static fromJSON(e){if(ge(e,Dt._jsonSchema))return new Dt(e.latitude,e.longitude)}}Dt._jsonSchemaVersion="firestore/geoPoint/1.0",Dt._jsonSchema={type:U("string",Dt._jsonSchemaVersion),latitude:U("number"),longitude:U("number")};/**
 * @license
 * Copyright 2024 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class kt{constructor(e){this._values=(e||[]).map((n=>n))}toArray(){return this._values.map((e=>e))}isEqual(e){return(function(o,a){if(o.length!==a.length)return!1;for(let d=0;d<o.length;++d)if(o[d]!==a[d])return!1;return!0})(this._values,e._values)}toJSON(){return{type:kt._jsonSchemaVersion,vectorValues:this._values}}static fromJSON(e){if(ge(e,kt._jsonSchema)){if(Array.isArray(e.vectorValues)&&e.vectorValues.every((n=>typeof n=="number")))return new kt(e.vectorValues);throw new N(P.INVALID_ARGUMENT,"Expected 'vectorValues' field to be a number array")}}}kt._jsonSchemaVersion="firestore/vectorValue/1.0",kt._jsonSchema={type:U("string",kt._jsonSchemaVersion),vectorValues:U("object")};function qr(r,e,n){if((e=de(e))instanceof zr)return e._internalPath;if(typeof e=="string")return gh(r,e);throw Dn("Field path arguments must be of type string or ",r)}const ph=new RegExp("[~\\*/\\[\\]]");function gh(r,e,n){if(e.search(ph)>=0)throw Dn(`Invalid field path (${e}). Paths must not contain '~', '*', '/', '[', or ']'`,r);try{return new zr(...e.split("."))._internalPath}catch{throw Dn(`Invalid field path (${e}). Paths must not be empty, begin with '.', end with '.', or contain '..'`,r)}}function Dn(r,e,n,o,a){let d=`Function ${e}() called with invalid data`;d+=". ";let f="";return new N(P.INVALID_ARGUMENT,d+r+f)}const wr="@firebase/firestore",vr="4.14.1";/**
 * @license
 * Copyright 2020 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */class Kr{constructor(e,n,o,a,d){this._firestore=e,this._userDataWriter=n,this._key=o,this._document=a,this._converter=d}get id(){return this._key.path.lastSegment()}get ref(){return new rt(this._firestore,this._converter,this._key)}exists(){return this._document!==null}data(){if(this._document){if(this._converter){const e=new mh(this._firestore,this._userDataWriter,this._key,this._document,null);return this._converter.fromFirestore(e)}return this._userDataWriter.convertValue(this._document.data.value)}}_fieldsProto(){var e;return((e=this._document)==null?void 0:e.data.clone().value.mapValue.fields)??void 0}get(e){if(this._document){const n=this._document.data.field(qr("DocumentSnapshot.get",e));if(n!==null)return this._userDataWriter.convertValue(n)}}}class mh extends Kr{data(){return super.data()}}class Re{constructor(e,n){this.hasPendingWrites=e,this.fromCache=n}isEqual(e){return this.hasPendingWrites===e.hasPendingWrites&&this.fromCache===e.fromCache}}class Bt extends Kr{constructor(e,n,o,a,d,f){super(e,n,o,a,f),this._firestore=e,this._firestoreImpl=e,this.metadata=d}exists(){return super.exists()}data(e={}){if(this._document){if(this._converter){const n=new Oe(this._firestore,this._userDataWriter,this._key,this._document,this.metadata,null);return this._converter.fromFirestore(n,e)}return this._userDataWriter.convertValue(this._document.data.value,e.serverTimestamps)}}get(e,n={}){if(this._document){const o=this._document.data.field(qr("DocumentSnapshot.get",e));if(o!==null)return this._userDataWriter.convertValue(o,n.serverTimestamps)}}toJSON(){if(this.metadata.hasPendingWrites)throw new N(P.FAILED_PRECONDITION,"DocumentSnapshot.toJSON() attempted to serialize a document with pending writes. Await waitForPendingWrites() before invoking toJSON().");const e=this._document,n={};return n.type=Bt._jsonSchemaVersion,n.bundle="",n.bundleSource="DocumentSnapshot",n.bundleName=this._key.toString(),!e||!e.isValidDocument()||!e.isFoundDocument()?n:(this._userDataWriter.convertObjectMap(e.data.value.mapValue.fields,"previous"),n.bundle=(this._firestore,this.ref.path,"NOT SUPPORTED"),n)}}Bt._jsonSchemaVersion="firestore/documentSnapshot/1.0",Bt._jsonSchema={type:U("string",Bt._jsonSchemaVersion),bundleSource:U("string","DocumentSnapshot"),bundleName:U("string"),bundle:U("string")};class Oe extends Bt{data(e={}){return super.data(e)}}class le{constructor(e,n,o,a){this._firestore=e,this._userDataWriter=n,this._snapshot=a,this.metadata=new Re(a.hasPendingWrites,a.fromCache),this.query=o}get docs(){const e=[];return this.forEach((n=>e.push(n))),e}get size(){return this._snapshot.docs.size}get empty(){return this.size===0}forEach(e,n){this._snapshot.docs.forEach((o=>{e.call(n,new Oe(this._firestore,this._userDataWriter,o.key,o,new Re(this._snapshot.mutatedKeys.has(o.key),this._snapshot.fromCache),this.query.converter))}))}docChanges(e={}){const n=!!e.includeMetadataChanges;if(n&&this._snapshot.excludesMetadataChanges)throw new N(P.INVALID_ARGUMENT,"To include metadata changes with your document changes, you must also pass { includeMetadataChanges:true } to onSnapshot().");return this._cachedChanges&&this._cachedChangesIncludeMetadataChanges===n||(this._cachedChanges=(function(a,d){if(a._snapshot.oldDocs.isEmpty()){let f=0;return a._snapshot.docChanges.map((v=>{const I=new Oe(a._firestore,a._userDataWriter,v.doc.key,v.doc,new Re(a._snapshot.mutatedKeys.has(v.doc.key),a._snapshot.fromCache),a.query.converter);return v.doc,{type:"added",doc:I,oldIndex:-1,newIndex:f++}}))}{let f=a._snapshot.oldDocs;return a._snapshot.docChanges.filter((v=>d||v.type!==3)).map((v=>{const I=new Oe(a._firestore,a._userDataWriter,v.doc.key,v.doc,new Re(a._snapshot.mutatedKeys.has(v.doc.key),a._snapshot.fromCache),a.query.converter);let A=-1,D=-1;return v.type!==0&&(A=f.indexOf(v.doc.key),f=f.delete(v.doc.key)),v.type!==1&&(f=f.add(v.doc),D=f.indexOf(v.doc.key)),{type:yh(v.type),doc:I,oldIndex:A,newIndex:D}}))}})(this,n),this._cachedChangesIncludeMetadataChanges=n),this._cachedChanges}toJSON(){if(this.metadata.hasPendingWrites)throw new N(P.FAILED_PRECONDITION,"QuerySnapshot.toJSON() attempted to serialize a document with pending writes. Await waitForPendingWrites() before invoking toJSON().");const e={};e.type=le._jsonSchemaVersion,e.bundleSource="QuerySnapshot",e.bundleName=Ka.newId(),this._firestore._databaseId.database,this._firestore._databaseId.projectId;const n=[],o=[],a=[];return this.docs.forEach((d=>{d._document!==null&&(n.push(d._document),o.push(this._userDataWriter.convertObjectMap(d._document.data.value.mapValue.fields,"previous")),a.push(d.ref.path))})),e.bundle=(this._firestore,this.query._query,e.bundleName,"NOT SUPPORTED"),e}}function yh(r){switch(r){case 0:return"added";case 2:case 3:return"modified";case 1:return"removed";default:return Fe(61501,{type:r})}}/**
 * @license
 * Copyright 2022 Google LLC
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */le._jsonSchemaVersion="firestore/querySnapshot/1.0",le._jsonSchema={type:U("string",le._jsonSchemaVersion),bundleSource:U("string","QuerySnapshot"),bundleName:U("string"),bundle:U("string")};(function(e,n=!0){ja(Be),$t(new Ht("firestore",((o,{instanceIdentifier:a,options:d})=>{const f=o.getProvider("app").getImmediate(),v=new dh(new $a(o.getProvider("auth-internal")),new za(f,o.getProvider("app-check-internal")),ih(f,a),f);return d={useFetchStreams:n,...d},v._setSettings(d),v}),"PUBLIC").setMultipleInstances(!0)),wt(wr,vr,e),wt(wr,vr,"esm2020")})();
