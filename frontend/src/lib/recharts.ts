// Recharts compatibility shim for TypeScript 5.x
// recharts v2 exports class-based components that no longer satisfy TypeScript 5's
// stricter JSX element type constraints when used with @types/react 18.3+.
// We re-export them cast as FC<any> so JSX type-checking passes without altering
// any runtime behaviour.
/* eslint-disable @typescript-eslint/no-explicit-any */
import type { FC } from 'react'
import * as _RC from 'recharts'

export const AreaChart       = _RC.AreaChart       as unknown as FC<any>
export const Area            = _RC.Area            as unknown as FC<any>
export const BarChart        = _RC.BarChart        as unknown as FC<any>
export const Bar             = _RC.Bar             as unknown as FC<any>
export const LineChart       = _RC.LineChart       as unknown as FC<any>
export const Line            = _RC.Line            as unknown as FC<any>
export const XAxis           = _RC.XAxis           as unknown as FC<any>
export const YAxis           = _RC.YAxis           as unknown as FC<any>
export const CartesianGrid   = _RC.CartesianGrid   as unknown as FC<any>
export const Tooltip         = _RC.Tooltip         as unknown as FC<any>
export const ResponsiveContainer = _RC.ResponsiveContainer as unknown as FC<any>
export const Legend          = _RC.Legend          as unknown as FC<any>
export const ReferenceLine   = _RC.ReferenceLine   as unknown as FC<any>
export const PieChart        = _RC.PieChart        as unknown as FC<any>
export const Pie             = _RC.Pie             as unknown as FC<any>
export const Cell            = _RC.Cell            as unknown as FC<any>
export const ComposedChart   = _RC.ComposedChart   as unknown as FC<any>
export const RadarChart      = _RC.RadarChart      as unknown as FC<any>
export const Radar           = _RC.Radar           as unknown as FC<any>
export const PolarGrid       = _RC.PolarGrid       as unknown as FC<any>
export const PolarAngleAxis  = _RC.PolarAngleAxis  as unknown as FC<any>
export const PolarRadiusAxis = _RC.PolarRadiusAxis as unknown as FC<any>
