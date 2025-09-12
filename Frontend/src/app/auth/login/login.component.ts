import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  email = '';
  password = '';
  error = '';

  constructor(private authService: AuthService, private router: Router) {}

  login() {
    this.authService.login({email: this.email, password: this.password}).subscribe({
      next: (res: any) => {
        this.authService.setToken(res.token); // backend returns JWT
        this.router.navigate(['/']); // navigates to home
      },
      error: err => {
        this.error = err.error.message || 'Login failed';
      }
    });
  }
}
