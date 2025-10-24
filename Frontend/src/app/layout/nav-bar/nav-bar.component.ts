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
  userRole: string | null = null;

  constructor(private authService: AuthService, public router: Router) {}

  ngOnInit(): void {
    this.authService.getCurrentUser().subscribe({
      next: user => {
        this.isLoggedIn = !!user;

        if (this.isLoggedIn) {
          this.authService.getUserRole().subscribe(role => {
            this.userRole = role;
          });
        } else {
          this.userRole = null;
        }
      },
      error: () => {
        this.isLoggedIn = false;
        this.userRole = null;
      }
    });
  }

  logout(): void {
    this.authService.logout().subscribe({
      next: () => {
        this.isLoggedIn = false;
        this.userRole = null;
        this.router.navigate(['/login']);
      },
      error: () => {
        this.isLoggedIn = false;
        this.userRole = null;
        this.router.navigate(['/login']);
      }
    });
  }
}
