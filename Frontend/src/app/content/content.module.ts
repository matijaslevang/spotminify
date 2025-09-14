import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ArtistViewComponent } from './artist/artist-view/artist-view.component';
import { SongViewComponent } from './song/song-view/song-view.component';
import { AlbumViewComponent } from './album/album-view/album-view.component';
import { SongCardComponent } from './song/song-card/song-card.component';
import { CreateArtistComponent } from './artist/create-artist/create-artist.component';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatOptionModule } from '@angular/material/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { ReactiveFormsModule, FormsModule } from '@angular/forms';

@NgModule({
  declarations: [
    ArtistViewComponent,
    SongViewComponent,
    AlbumViewComponent,
    SongCardComponent,
    CreateArtistComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatOptionModule,
    MatButtonModule,
    MatIconModule
  ]
})
export class ContentModule { }
