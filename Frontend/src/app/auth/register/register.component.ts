import { Component, inject, OnInit } from '@angular/core';
import { AuthService } from '../auth.service';
import { Router } from '@angular/router';
import { AbstractControl, FormControl, FormGroup, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import {MatSnackBar} from '@angular/material/snack-bar';

@Component({
  selector: 'app-register',
  templateUrl: './register.component.html',
  styleUrl: './register.component.css'
})
export class RegisterComponent {
  registerForm = new FormGroup({
    email: new FormControl('', [Validators.required, Validators.email]),
    username: new FormControl('', [Validators.required, Validators.minLength(8)]),
    password: new FormControl('', [Validators.required, Validators.minLength(8)]),
    confirmPassword: new FormControl('', [Validators.required, Validators.minLength(8)]),
    firstName: new FormControl('', Validators.required),
    lastName: new FormControl('', Validators.required),
    birthDate: new FormControl('', Validators.required)
  },
    { validators: MatchValidator('password', 'confirmPassword') });
  snackBar:MatSnackBar = inject(MatSnackBar);
  error: string = '';

  constructor(private authService: AuthService, private router: Router) {}

  register() {
    if(!this.registerForm.valid)
      return;

    this.authService.register({
      email: this.registerForm.value.email,
      username: this.registerForm.value.username,
      password: this.registerForm.value.password,
      firstName: this.registerForm.value.firstName,
      lastName: this.registerForm.value.lastName,
      birthDate: this.registerForm.value.birthDate
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
export function MatchValidator(controlName: string, matchingControlName: string): ValidatorFn {
  return (formGroup: AbstractControl): ValidationErrors | null => {
    const control = formGroup.get(controlName);
    const matchingControl = formGroup.get(matchingControlName);
    if (!control || !matchingControl) {
      return null; // Return null if controls are missing
    }

    if (matchingControl.errors && !matchingControl.errors['mismatch']) {
      return null; // Skip if another validator has found an error
    }

    if (control.value !== matchingControl.value) {
      matchingControl.setErrors({ mismatch: true });
      return { mismatch: true };
    } else {
      matchingControl.setErrors(null); // Clear mismatch error if values match
    }

    return null;
  };
}

