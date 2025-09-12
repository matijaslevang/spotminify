import { Component, OnInit } from '@angular/core';
import { AuthService } from '../../auth/auth.service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-nav-bar',
  templateUrl: './nav-bar.component.html',
  styleUrl: './nav-bar.component.css'
})
export class NavBarComponent implements OnInit{
  role: string | null = '';
  constructor(private authService: AuthService, private router: Router) {
  }

  ngOnInit(): void {
    // To-do: get the role
    // this.authService.getRole.subscribe((result) => {
    //   this.role = result;
    // })
  }

  logout(): void{
    // To do
  }

}
