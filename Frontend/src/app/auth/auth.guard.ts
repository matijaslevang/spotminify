import { Injectable } from '@angular/core';
import { CanActivate, ActivatedRouteSnapshot, Router } from '@angular/router';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate {

  constructor(private router: Router) {}

  canActivate(route: ActivatedRouteSnapshot): boolean {
    const token = localStorage.getItem('token');

    if (!token) {
      this.router.navigate(['login']);
      return false;
    }

    try {
      // Parse JWT to find role
      const payload = JSON.parse(atob(token.split('.')[1]));
      const groups = payload['cognito:groups'] || [];
      const userRole = groups[0] || null;

      if (!userRole) {
        this.router.navigate(['login']);
        return false;
      }

      // Check role
      const allowedRoles = route.data['role'] as string[]; 
      if (allowedRoles && !allowedRoles.includes(userRole)) {
        this.router.navigate(['home']);
        return false;
      }

      return true;

    } catch (err) {
      console.error('Invalid token', err);
      this.router.navigate(['login']);
      return false;
    }
  }
}
