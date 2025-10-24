import { Injectable } from '@angular/core';
import { Observable, from, map } from 'rxjs';
import { 
  signUp, 
  signIn, 
  signOut, 
  fetchAuthSession, 
  getCurrentUser, 
  confirmSignUp 
} from 'aws-amplify/auth';

@Injectable({
  providedIn: 'root'
})
export class AuthService {

  constructor() {}

  register(data: { 
    email: string, 
    username: string, 
    password: string, 
    firstName: string, 
    lastName: string, 
    birthDate: string 
  }): Observable<any> {
    return from(
      signUp({
        username: data.username,
        password: data.password,
        options: {
          userAttributes: {
            email: data.email,
            given_name: data.firstName,
            family_name: data.lastName,
            birthdate: data.birthDate,
            'custom:role': 'User'
          }
        }
      })
    );
  }

  confirmRegistration(username: string, code: string): Observable<any> {
    return from(confirmSignUp({ username, confirmationCode: code }));
  }

  login(data: { username: string, password: string }): Observable<any> {
    return from(signIn({ 
      username: data.username, 
      password: data.password 
    }));
  }

  logout(): Observable<any> {
    return from(signOut());
  }

  getCurrentUser(): Observable<any> {
    return from(getCurrentUser());
  }

  getUserRole(): Observable<string | null> {
    return from(fetchAuthSession()).pipe(
      map((session: any) => {
        const idToken = session.tokens?.idToken?.payload;
        if (!idToken) return null;

        if (idToken['custom:role']) {
          return idToken['custom:role'];
        }

        return null;
      })
    );
  }

  getSession(): Observable<any> {
    return from(fetchAuthSession());
  }

  getIdToken(): Observable<string | null> {
    return from(fetchAuthSession()).pipe(
      map((session: any) => session.tokens?.idToken?.toString() ?? null)
    );
  }

}
