import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../enviroment';
import { Observable } from 'rxjs';
export interface PresignReq { bucketType: 'audio'|'image'; fileName: string; contentType: string; }
export interface PresignRes { url: string; key: string; bucket: string; }

export interface SingleDto {
  ContentType: 'SINGLE';
  ContentName: string;
  SongRef: string;                 // s3://bucket/key
  SongImage?: string | null;
  Artists: string[];
  Genres: string[];
  trackNo: number;
  explicit: boolean;
  albumId?: string | null;
}

export interface AlbumDto {
  ContentType: 'ALBUM';
  ContentName: string;
  AlbumImage?: string | null;
  Artists: string[];
  Genres: string[];
  albumId?: string | null;
  releaseYear?: number | null;
}

@Injectable({ providedIn: 'root' })
export class UploadService {
  private base = environment.apiUrl;

  constructor(private httpClient: HttpClient) {}

  // Uzmi JWT iz svog auth sloja; po potrebi zameni implementaciju
  private authHeaders(): HttpHeaders {
    const token = localStorage.getItem('idToken') || '';
    return token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : new HttpHeaders();
  }

    getPresignedUrl(p: PresignReq) {
    return this.httpClient.post<PresignRes>(
      `${this.base}upload-url`,
      p,
      { headers: this.authHeaders() }
    );
  }

  async putToS3(url: string, file: File): Promise<Response> {
    return fetch(url, {
      method: 'PUT',
      body: file,
      headers: { 'Content-Type': file.type }
    });
  }

createSingle(payload: any): Observable<any> {
console.log('createSingle payload:', payload); 
return this.httpClient.post(
    `${environment.apiUrl}singles`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
);
}

createAlbum(payload: any): Observable<any> {
console.log('createAlbum payload:', payload); 
return this.httpClient.post(
    `${environment.apiUrl}albums`,
    payload,
    { headers: { 'Content-Type': 'application/json' } }
);
}



}
