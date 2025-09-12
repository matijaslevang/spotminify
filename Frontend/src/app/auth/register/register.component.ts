import { Component } from '@angular/core';
import { AuthService } from '../auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrl: './register.component.css'
})
export class RegisterComponent {
  email = '';
  password = '';
  firstName = '';
  lastName = '';
  birthDate = '';
  error = '';

  constructor(private authService: AuthService, private router: Router) {}

  register() {
    this.authService.register({
      email: this.email,
      password: this.password,
      firstName: this.firstName,
      lastName: this.lastName,
      birthDate: this.birthDate
    }).subscribe({
      next: res => {
        this.router.navigate(['/login']);
      },
      error: err => {
        this.error = err.error.message || 'Registration failed';
      }
    });
  }
}
