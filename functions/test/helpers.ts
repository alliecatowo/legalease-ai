/** In-memory fakes used by the tenant-isolation tests. */

type Cond = Record<string, any>

/** Evaluates the subset of Qdrant filter syntax this codebase emits. */
export function matches(payload: Record<string, any>, f: Cond | undefined): boolean {
  if (!f) return true
  if (f.key !== undefined) {
    const v = payload[f.key]
    if ('value' in f.match) return v === f.match.value
    if ('any' in f.match) return f.match.any.includes(v)
    throw new Error('unsupported match')
  }
  const must = (f.must ?? []).every((c: Cond) => matches(payload, c))
  const should = f.should === undefined || f.should.some((c: Cond) => matches(payload, c))
  const mustNot = (f.must_not ?? []).every((c: Cond) => !matches(payload, c))
  return must && should && mustNot
}

export class FakeQdrant {
  points: Array<{ id: string; vector: number[]; payload: Record<string, any> }> = []
  async getCollection() { return {} }
  async createCollection() {}
  async upsert(_c: string, { points }: { points: any[] }) { this.points.push(...points) }
  async search(_c: string, { filter, limit }: { filter?: Cond; limit: number }) {
    return this.points
      .filter(p => matches(p.payload, filter))
      .slice(0, limit)
      .map(p => ({ id: p.id, score: 0.99, payload: p.payload }))
  }
  async delete(_c: string, { filter }: { filter: Cond }) {
    this.points = this.points.filter(p => !matches(p.payload, filter))
    return { status: 'completed' }
  }
}

export class FakeDb {
  constructor(public docs: Record<string, Record<string, any>> = {}) {}
  doc(path: string) {
    return {
      get: async () => ({
        exists: path in this.docs,
        id: path.split('/').pop()!,
        data: () => this.docs[path]
      })
    }
  }
  collectionGroup(id: string) {
    return {
      where: (field: string, _op: '==', value: unknown) => ({
        get: async () => ({
          docs: Object.entries(this.docs)
            .filter(([p, d]) => p.split('/').at(-2) === id && d[field] === value)
            .map(([p, d]) => ({
              ref: { parent: { parent: { id: p.split('/')[1]! } } },
              data: () => d
            }))
        })
      })
    }
  }
}
