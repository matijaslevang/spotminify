import { Component, OnInit } from '@angular/core';
import { FormBuilder, Validators, FormGroup } from '@angular/forms';
import { UploadService } from '../upload.service';
import { from, of } from 'rxjs';
import { switchMap, concatMap, map, finalize } from 'rxjs/operators';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-admin',
  templateUrl: './admin.component.html',
  styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {
  isSubmittingSingle = false;
  isSubmittingAlbum  = false;

  // left side
  files: File[] = [];
  cover?: File;
  coverPreview?: string | ArrayBuffer | null;

  // tabs
  tabIndex = 0; // 0 = single, 1 = album

  // options
  genreOptions: string[] = [
    'Pop','Rock','Hip-Hop','R&B','Electronic','House','Techno','Jazz','Classical','Folk','Indie','Metal'
  ];

  // forms
  singleForm!: FormGroup;
  albumForm!: FormGroup;

  constructor(private fb: FormBuilder, private api: UploadService, private snack: MatSnackBar) {}


  ngOnInit() {
    this.singleForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      genres: [[] as string[]],
      artistIds: [''],
      trackNo: [1],
      releaseDate: [''],
      explicit: [false]
    });

    this.albumForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      genres: [[] as string[]],
      artistIds: [''],
      albumId: [''],
      releaseYear: [new Date().getFullYear(), [Validators.min(1900), Validators.max(2999)]]
    });
  }

  // left side handlers
  onFilesSelected(ev: Event) {
    const input = ev.target as HTMLInputElement;
    if (input.files && input.files.length) this.files = Array.from(input.files);
  }
  onCoverSelected(ev: Event) {
    const input = ev.target as HTMLInputElement;
    if (input.files && input.files.length) {
      this.cover = input.files[0];
      const reader = new FileReader();
      reader.onload = () => (this.coverPreview = reader.result);
      reader.readAsDataURL(this.cover);
    }
  }
  onDragOver(e: DragEvent) { e.preventDefault(); }
  onDrop(e: DragEvent) {
    e.preventDefault();
    const list = e.dataTransfer?.files;
    if (list && list.length) this.files = Array.from(list);
  }
  remove(index: number) {
    this.files.splice(index, 1);
    this.files = [...this.files];
  }

 /*
 submitSingle() {
  if (!this.files.length || this.singleForm.invalid) return;
  this.isSubmittingSingle = true;
  const file = this.files[0];

  this.api.getPresignedUrl({ bucketType: 'audio', fileName: file.name, contentType: file.type }).pipe(
    switchMap(up => from(this.api.putToS3(up.url, file)).pipe(map(() => ({ up })))),
    switchMap(({ up }) =>
      this.cover
        ? this.api.getPresignedUrl({ bucketType: 'image', fileName: this.cover.name, contentType: this.cover.type }).pipe(
            switchMap(cup => from(this.api.putToS3(cup.url, this.cover!)).pipe(
              map(() => ({ up, coverUrl: `s3://${cup.bucket}/${cup.key}` }))
            ))
          )
        : of({ up, coverUrl: null as string | null })
    ),
    switchMap(({ up, coverUrl }) => this.api.createSingle({
      ContentType: 'SINGLE',
      ContentName: this.singleForm.value.title!,
      SongRef: `s3://${up.bucket}/${up.key}`,
      SongImage: coverUrl,
      SongArtists: (this.singleForm.value.artistIds || '').split(',').map((s: string) => s.trim()).filter(Boolean),
      SongGenres: this.singleForm.value.genres as string[],
      trackNo: Number(this.singleForm.value.trackNo) || 1,
      explicit: !!this.singleForm.value.explicit,
      albumId: null
    })),
    finalize(() => this.isSubmittingSingle = false)
  ).subscribe({
    next: () => { this.ok('Single created'); this.resetSingle(); this.files = []; this.cover = undefined; this.coverPreview = null; },
    error: (e) => this.err(`Failed to create single: ${e?.error?.message || e?.message || 'Unknown error'}`)
  });
}
submitAlbum() {
  if (!this.files.length || this.albumForm.invalid) return;
  this.isSubmittingAlbum = true;

  const cover$ = this.cover
    ? this.api.getPresignedUrl({ bucketType: 'image', fileName: this.cover.name, contentType: this.cover.type }).pipe(
        switchMap(cup => from(this.api.putToS3(cup.url, this.cover!)).pipe(map(() => `s3://${cup.bucket}/${cup.key}`)))
      )
    : of(null as string | null);

  cover$.pipe(
    switchMap(coverUrl => this.api.createAlbum({
      ContentType: 'ALBUM',
      ContentName: this.albumForm.value.title!,
      AlbumImage: coverUrl,
      AlbumArtists: (this.albumForm.value.artistIds || '').split(',').map((s: string) => s.trim()).filter(Boolean),
      AlbumGenres: this.albumForm.value.genres as string[],
      albumId: this.albumForm.value.albumId || null,
      releaseYear: this.albumForm.value.releaseYear || null
    }).pipe(map(res => ({ albumId: res.albumId, coverUrl })))),
    switchMap(({ albumId, coverUrl }) =>
      from(this.files).pipe(
        concatMap((f, idx) =>
          this.api.getPresignedUrl({ bucketType: 'audio', fileName: f.name, contentType: f.type }).pipe(
            switchMap(up => from(this.api.putToS3(up.url, f)).pipe(
              switchMap(() => this.api.createSingle({
                ContentType: 'SINGLE',
                ContentName: f.name,
                SongRef: `s3://${up.bucket}/${up.key}`,
                SongImage: coverUrl,
                SongArtists: (this.albumForm.value.artistIds || '').split(',').map((s: string) => s.trim()).filter(Boolean),
                SongGenres: this.albumForm.value.genres as string[],
                trackNo: idx + 1,
                explicit: false,
                albumId
              }))
            ))
          )
        ),
        finalize(() => this.isSubmittingAlbum = false)
      )
    )
  ).subscribe({
    next: () => {}, // pojedinačni track OK
    error: (e) => this.err(`Album creation failed: ${e?.error?.message || e?.message || 'Unknown error'}`),
    complete: () => {
      this.ok('Album created');
      this.resetAlbum(); this.files = []; this.cover = undefined; this.coverPreview = null;
    }
  });
}
*/
  submitSingle() {
  if (this.singleForm.invalid) return;
  this.isSubmittingSingle = true;

  const body = {
    ContentType: 'SINGLE',
    ContentName: this.singleForm.value.title!,
    SongRef: 's3://audio/placeholder.mp3',   // TEMP
    // SongImage: null,                          // TEMP
    SongArtists: (this.singleForm.value.artistIds || '').split(',').map((s:string)=>s.trim()).filter(Boolean),
    SongGenres: this.singleForm.value.genres as string[],
    trackNo: Number(this.singleForm.value.trackNo) || 1,
    explicit: !!this.singleForm.value.explicit,
    // albumId: null
  };

  this.api.createSingle(body).subscribe({
    next: () => { this.ok('Single created'); this.resetSingle(); this.files=[]; this.cover=undefined; this.coverPreview=null; },
    error: e => this.err(`Failed: ${e?.error?.message || e?.message || 'Unknown error'}`)
  }).add(() => this.isSubmittingSingle = false);
}

submitAlbum() {
  if (this.albumForm.invalid) return;
  this.isSubmittingAlbum = true;

  const albumBody = {
    ContentType: 'ALBUM',
    ContentName: this.albumForm.value.title!,
    //AlbumImage: null,  // TEMP
    AlbumArtists: (this.albumForm.value.artistIds || '').split(',').map((s:string)=>s.trim()).filter(Boolean),
    AlbumGenres: this.albumForm.value.genres as string[],
    albumId: this.albumForm.value.albumId || null,
    releaseYear: this.albumForm.value.releaseYear || null
  };

  this.api.createAlbum(albumBody).subscribe({
    next: () => {
      this.ok('Album created');
      this.resetAlbum(); this.files=[]; this.cover=undefined; this.coverPreview=null;
    },
    error: e => this.err(`Album failed: ${e?.error?.message || e?.message || 'Unknown error'}`)
  }).add(() => this.isSubmittingAlbum = false);
}



  // reset
  resetSingle() {
    this.singleForm.reset({
      title: '',
      genres: [],
      artistIds: '',
      trackNo: 1,
      releaseDate: '',
      explicit: false
    });
  }
  resetAlbum() {
    this.albumForm.reset({
      title: '',
      genres: [],
      artistIds: '',
      albumId: '',
      releaseYear: new Date().getFullYear()
    });
  }

  // util
  getCreatedAt(f: File) { return new Date(f.lastModified).toLocaleString(); }
  getUpdatedAt(f: File) { return new Date(f.lastModified).toLocaleString(); }


  private ok(msg: string)  { this.snack.open(msg, 'OK', { duration: 2500 }); }
  private err(msg: string) { this.snack.open(msg, 'Close', { panelClass: 'snack-error' }); }
}