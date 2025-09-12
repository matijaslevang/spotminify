import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'https://53hzf6rmba.execute-api.eu-central-1.amazonaws.com/prod/';

  constructor(private http: HttpClient) {}

  register(data: {email: string, username: string, password: string, firstName: string, lastName: string, birthDate: string}): Observable<any> {
    return this.http.post(`${this.apiUrl}/register`, data);
  }

  login(data: {email: string, password: string}): Observable<any> {
    return this.http.post(`${this.apiUrl}/login`, data);
  }

  logout() {
    localStorage.removeItem('token');
  }

  setToken(token: string) {
    localStorage.setItem('token', token);
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }
}
