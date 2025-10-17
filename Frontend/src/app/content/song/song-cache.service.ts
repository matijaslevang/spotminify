import { Injectable } from '@angular/core';
import { openDB, IDBPDatabase } from 'idb';

@Injectable({
  providedIn: 'root'
})
export class SongCacheService {
  private dbp: Promise<IDBPDatabase<any>>;

  constructor() {
    this.dbp = openDB('offline-audio', 1, {
      upgrade(db) { db.createObjectStore('songs'); }
    });
  }

  async isCached(id: string | number): Promise<boolean> {
    return !!(await (await this.dbp).get('songs', String(id)));
  }

  async getObjectUrl(id: string | number): Promise<string | null> {
    const blob = await (await this.dbp).get('songs', String(id));
    return blob ? URL.createObjectURL(blob) : null;
    // Napomena: čuvaj referencu i zovi URL.revokeObjectURL(...) kad menjaš izvor da ne curi memorija.
  }

  async download(id: string | number, url: string): Promise<void> {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Download failed');
    const blob = await res.blob();
    await (await this.dbp).put('songs', blob, String(id));
  }

  async remove(id: string | number): Promise<void> {
    await (await this.dbp).delete('songs', String(id));
  }
}
