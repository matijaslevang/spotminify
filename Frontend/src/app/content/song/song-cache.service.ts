import { Injectable } from '@angular/core';
import { openDB, IDBPDatabase } from 'idb';

const DB_NAME = 'OfflineAudioDB';
const STORE_NAME = 'Songs';

@Injectable({
  providedIn: 'root'
})
export class SongCacheService {
  private dbPromise: Promise<IDBPDatabase>;

    constructor() {
      this.dbPromise = openDB(DB_NAME, 1, {
        upgrade(db) {
          db.createObjectStore(STORE_NAME);
          console.log(`IndexedDB: Store '${STORE_NAME}' created.`);
        },
      });
    }

    /**
     * Preuzima audio fajl sa date URL adrese i kešira ga u IndexedDB.
     * @param songId ID pesme (koristi se kao ključ za skladištenje)
     * @param audioUrl Direktni URL S3 fajla (npr. 'https://s3.amazonaws.com/bucket/audio/pesma.mp3')
     */
    async download(songId: string, audioUrl: string): Promise<void> {
      console.log(`Caching: Attempting to download ${songId} from ${audioUrl}`);
      
      const response = await fetch(audioUrl);

      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const audioBlob = await response.blob();
   
      const db = await this.dbPromise;
      await db.put(STORE_NAME, audioBlob, songId);
      
      console.log(`Caching: Successfully saved ${songId} to IndexedDB.`);
    }

    /**
     * Proverava IndexedDB i vraća lokalni Blob URL ako je pesma keširana.
     * @param songId ID pesme
     * @returns Lokalni Blob URL (npr. 'blob:http://...') ili null
     */
    async getObjectUrl(songId: string): Promise<string | null> {
      const db = await this.dbPromise;

      const audioBlob = await db.get(STORE_NAME, songId);

      if (audioBlob instanceof Blob) {
        const blobUrl = URL.createObjectURL(audioBlob);
        return blobUrl;
      }
      
      return null;
    }
  }