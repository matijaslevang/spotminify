import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { environment } from '../../enviroment';
export interface PresignReq { bucketType: 'audio'|'image'; fileName: string; contentType: string; }
export interface PresignRes { url: string; key: string; bucket: string; }

export interface SingleDto {
  ContentType: 'SINGLE';
  ContentName: string;
  SongRef: string;                 // s3://bucket/key
  SongImage?: string | null;
  SongArtists: string[];
  SongGenres: string[];
  trackNo: number;
  explicit: boolean;
  albumId?: string | null;
}

export interface AlbumDto {
  ContentType: 'ALBUM';
  ContentName: string;
  AlbumImage?: string | null;
  AlbumArtists: string[];
  AlbumGenres: string[];
  albumId?: string | null;
  releaseYear?: number | null;
}

@Injectable({ providedIn: 'root' })
export class UploadService {
  private base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // Uzmi JWT iz svog auth sloja; po potrebi zameni implementaciju
  private authHeaders(): HttpHeaders {
    const token = localStorage.getItem('idToken') || '';
    return token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : new HttpHeaders();
  }

  getPresignedUrl(p: PresignReq) { 
    return this.http.post<PresignRes>(`${this.base}/upload-url`, p, { headers: this.authHeaders() });
  }

  async putToS3(url: string, file: File): Promise<Response> {
    return fetch(url, { method: 'PUT', body: file, headers: { 'Content-Type': file.type } });
  }
  /*
  createSingle(dto: SingleDto) {
    return this.http.post<{ contentId: string }>(`${this.base}/contents/single`, dto, { headers: this.authHeaders() });
  }

  createAlbum(dto: AlbumDto) {
    return this.http.post<{ albumId: string }>(`${this.base}/contents/album`, dto, { headers: this.authHeaders() });
  }*/
 createSingle(body: any) {
  return this.http.post(`${this.base}/contents/single`, body);
}
createAlbum(body: any) {
  return this.http.post(`${this.base}/contents/album`, body);
}

}
