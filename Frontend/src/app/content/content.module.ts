import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ArtistViewComponent } from './artist/artist-view/artist-view.component';
import { SongViewComponent } from './song/song-view/song-view.component';
import { AlbumViewComponent } from './album/album-view/album-view.component';
import { SongCardComponent } from './song/song-card/song-card.component';
import { AlbumCardComponent } from './album/album-card/album-card.component';
import { ArtistCardComponent } from './artist/artist-card/artist-card.component';
import { MatButton } from "@angular/material/button";



@NgModule({
  declarations: [
    ArtistViewComponent,
    SongViewComponent,
    AlbumViewComponent,
    SongCardComponent,
    AlbumCardComponent,
    ArtistCardComponent
  ],
  imports: [
    CommonModule,
    MatButton
],
  exports: [
    SongCardComponent,
    AlbumCardComponent,
    ArtistCardComponent,
  ]
})
export class ContentModule { }
