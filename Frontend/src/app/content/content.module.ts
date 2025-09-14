import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ArtistViewComponent } from './artist/artist-view/artist-view.component';
import { SongViewComponent } from './song/song-view/song-view.component';
import { AlbumViewComponent } from './album/album-view/album-view.component';
import { SongCardComponent } from './song/song-card/song-card.component';



@NgModule({
  declarations: [
    ArtistViewComponent,
    SongViewComponent,
    AlbumViewComponent,
    SongCardComponent
  ],
  imports: [
    CommonModule
  ]
})
export class ContentModule { }
