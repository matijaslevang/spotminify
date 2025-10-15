import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { LoginComponent } from './auth/login/login.component';
import { RegisterComponent } from './auth/register/register.component';
import { HomeComponent } from './layout/home/home.component';
import { ArtistViewComponent } from './content/artist/artist-view/artist-view.component';
import { SongViewComponent } from './content/song/song-view/song-view.component';
import { AlbumViewComponent } from './content/album/album-view/album-view.component';
import { CreateArtistComponent } from './content/artist/create-artist/create-artist.component';
import { DiscoverPageComponent } from './layout/discover-page/discover-page.component';
import { SubscriptionManagementComponent } from './layout/subscription-management/subscription-management.component';

const routes: Routes = [
  { path: '', redirectTo: '/home', pathMatch: 'full' },
  { path: 'login', component: LoginComponent },
  { path: 'register', component: RegisterComponent },
  { path: 'home', component:HomeComponent },
  { path: 'artist', component: ArtistViewComponent },
  { path: 'song', component: SongViewComponent },
  { path: 'album', component: AlbumViewComponent },
  { path: 'create-artist', component: CreateArtistComponent },
  { path: 'discover', component: DiscoverPageComponent },
  { path: 'my-subscriptions', component: SubscriptionManagementComponent },
  { path: '**', redirectTo: 'home' },
];

@NgModule({
  imports: [RouterModule.forRoot(routes)],
  exports: [RouterModule]
})
export class AppRoutingModule {}
