import { Component, OnInit } from '@angular/core';
import { AuthService } from '../../auth/auth.service';
import { Router } from '@angular/router';
import { Observable } from 'rxjs';

@Component({
  selector: 'app-nav-bar',
  templateUrl: './nav-bar.component.html',
  styleUrls: ['./nav-bar.component.css']
})
export class NavBarComponent implements OnInit {
  isLoggedIn: boolean = false;

  constructor(private authService: AuthService, public router: Router) {}

  ngOnInit(): void {
    this.authService.getCurrentUser().subscribe({
      next: user => {
        this.isLoggedIn = !!user;
      },
      error: () => {
        this.isLoggedIn = false;
      }
    });
  }

  logout(): void {
    this.authService.logout().subscribe({
      next: () => {
        this.isLoggedIn = false;
        this.router.navigate(['/login']);
      },
      error: () => {
        this.isLoggedIn = false;
        this.router.navigate(['/login']);
      }
    });
  }
}
