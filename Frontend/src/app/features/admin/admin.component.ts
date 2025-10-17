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
  // State
  isSubmittingSingle = false;
  isSubmittingAlbum = false;

  files: File[] = [];
  cover?: File;
  coverPreview?: string | ArrayBuffer | null;

  tabIndex = 0; // 0 = single, 1 = album

  // Wizard step
  albumStep = 0;

  genreOptions: string[] = ['Pop', 'Rock', 'Hip-Hop', 'R&B', 'Electronic', 'House', 'Techno', 'Jazz', 'Classical', 'Folk', 'Indie', 'Metal'];

  // Dropdown za artiste - možeš učitavati dinamički sa API-ja ako treba
  artistOptions: { id: string, name: string }[] = [
    { id: '1', name: 'Artist A' },
    { id: '2', name: 'Artist B' },
    { id: '3', name: 'Artist C' }
  ];

  singleForm!: FormGroup;
  albumForm!: FormGroup;
  albumSingleForm!: FormGroup;

  // Kolekcija singlova za album
  albumSingles: Array<{ title: string; genres: string[]; artistIds: string[]; fileIndex: number }> = [];

  constructor(private fb: FormBuilder, private api: UploadService, private snack: MatSnackBar) {}

  ngOnInit() {
    this.singleForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      genres: [[] as string[]],
      artistIds: [[] as string[]],
      explicit: [false]
    });

    this.albumForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      genres: [[] as string[]],
      artistIds: [[] as string[]]
    });

    this.albumSingleForm = this.fb.group({
      title: ['', [Validators.required, Validators.maxLength(200)]],
      genres: [[] as string[]],
      artistIds: [[] as string[]],
      fileIndex: [null, [Validators.required]]
    });
  }

  // Handleri za fajlove
  onFilesSelected(ev: Event) {
    const input = ev.target as HTMLInputElement;
    if (input.files) {
      this.addFiles(Array.from(input.files));
      input.value = ''; // Reset za ponovno biranje
    }
  }

  onDragOver(e: DragEvent) {
    e.preventDefault();
  }

  onDrop(e: DragEvent) {
    e.preventDefault();
    if (e.dataTransfer?.files) {
      this.addFiles(Array.from(e.dataTransfer.files));
    }
  }

  private addFiles(newFiles: File[]) {
    // Filtriraj samo audio fajlove
    const audioFiles = newFiles.filter(f => f.type.startsWith('audio/'));
    if (audioFiles.length < newFiles.length) {
      this.snack.open('Only audio files are accepted', 'Close', { duration: 3000 });
    }
    this.files = [...this.files, ...audioFiles];
  }

  remove(index: number) {
    this.files.splice(index, 1);
    // Ažuriraj fileIndex u albumSingles ako treba
    this.albumSingles = this.albumSingles.filter(s => s.fileIndex !== index)
      .map(s => ({ ...s, fileIndex: s.fileIndex > index ? s.fileIndex - 1 : s.fileIndex }));
  }

  // Handleri za cover
  onCoverSelected(ev: Event) {
    const input = ev.target as HTMLInputElement;
    if (input.files?.[0]) {
      this.setCover(input.files[0]);
      input.value = '';
    }
  }

  onCoverDrop(e: DragEvent) {
    e.preventDefault();
    if (e.dataTransfer?.files?.[0]) {
      this.setCover(e.dataTransfer.files[0]);
    }
  }

  private setCover(file: File) {
    if (!file.type.startsWith('image/')) {
      this.snack.open('Only images are accepted for cover', 'Close', { duration: 3000 });
      return;
    }
    this.cover = file;
    const reader = new FileReader();
    reader.onload = () => this.coverPreview = reader.result;
    reader.readAsDataURL(file);
  }

  removeCover() {
    this.cover = undefined;
    this.coverPreview = null;
  }

  // Helper za B64
  private readAsB64(file: File): Promise<string> {
    return new Promise((res, rej) => {
      const r = new FileReader();
      r.onload = () => res((r.result as string).split(',')[1]);
      r.onerror = rej;
      r.readAsDataURL(file);
    });
  }

  renderArtistNames(ids: string[]): string {
    const map = new Map(this.artistOptions.map(a => [a.id, a.name]));
    return ids.map(id => map.get(id) || id).join(', ');
  }

  // SINGLE SUBMIT
  async submitSingle() {
  if (this.singleForm.invalid || !this.files.length) {
    this.snack.open('Choose an audio file', 'Close', { panelClass: 'snack-error' });
    return;
  }
  this.isSubmittingSingle = true;
  try {
    const audioFile = this.files[0];
    const audioContentType = audioFile.type || 'audio/mpeg';
    // 1) presign audio
    const presA = await this.api.getPresignedUrl({
      bucketType: 'audio',
      fileName: audioFile.name,
      contentType: audioContentType
    }).toPromise();

    // 2) PUT na S3
    await this.api.putToS3(presA!.url, audioFile, audioContentType);

    // 3) presign cover (opciono)
    let imageKey: string | undefined;
    if (this.cover) {
      const presI = await this.api.getPresignedUrl({
        bucketType: 'image',
        fileName: this.cover.name,
        contentType: this.cover.type || 'image/jpeg'
      }).toPromise();
      await this.api.putToS3(presI!.url, this.cover, this.cover.type);
      imageKey = presI!.key;
    }

    // 4) POST /singles sa key-evima
    const payload = {
      title: this.singleForm.value.title,
      artistIds: this.singleForm.value.artistIds,
      genres: this.singleForm.value.genres,
      explicit: !!this.singleForm.value.explicit,
      audioKey: presA!.key,
      ...(imageKey ? { imageKey } : {})
    };

    this.api.createSingle(payload).subscribe({
      next: () => {
        this.snack.open('Single created', 'OK', { duration: 2500 });
        this.resetSingle();
        this.files = []; this.cover = undefined; this.coverPreview = null;
      },
      error: (e) => this.snack.open(e?.error?.error || e?.error?.message || 'Failed', 'Close', { panelClass: 'snack-error' })
    });
  } catch {
    this.snack.open('Upload failed', 'Close', { panelClass: 'snack-error' });
  } finally {
    this.isSubmittingSingle = false;
  }
}

  // submitSingle() {
  //   if (this.singleForm.invalid || !this.files.length) {
  //     this.snack.open('Choose an audio file', 'Close', { panelClass: 'snack-error' });
  //     return;
  //   }
  //   this.isSubmittingSingle = true;

  //   const audioFile = this.files[0];
  //   Promise.all([
  //     this.readAsB64(audioFile),
  //     this.cover ? this.readAsB64(this.cover) : Promise.resolve(undefined)
  //   ]).then(([audioB64, coverB64]) => {
  //     const payload: any = {
  //       ContentType: 'SINGLE',
  //       ContentName: this.singleForm.value.title,
  //       Artists: this.singleForm.value.artistIds,
  //       Genres: this.singleForm.value.genres,
  //       explicit: !!this.singleForm.value.explicit,
  //       audio: audioB64,
  //       audioType: audioFile.type.split('/')[1] || 'mpeg',
  //       ...(coverB64 ? { image: coverB64, imageType: this.cover!.type.split('/')[1] || 'jpg' } : {})
  //     };

  //     this.api.createSingle(payload).subscribe({
  //       next: () => {
  //         this.snack.open('Single created', 'OK', { duration: 2500 });
  //         this.resetSingle();
  //         this.files = []; this.cover = undefined; this.coverPreview = null;
  //       },
  //       error: (e) => this.snack.open(e?.error?.error || e?.error?.message || 'Failed', 'Close', { panelClass: 'snack-error' })
  //     }).add(() => this.isSubmittingSingle = false);
  //   }).catch(() => {
  //     this.snack.open('Failed to read file(s)', 'Close', { panelClass: 'snack-error' });
  //     this.isSubmittingSingle = false;
  //   });
  // }

  // WIZARD NAV
  goToSingles() { this.albumStep = 1; }
  backToAlbum() { this.albumStep = 0; }

  // ADD single u listu
  addAlbumSingle() {
    if (this.albumSingleForm.invalid) return;
    this.albumSingles.push({ ...this.albumSingleForm.value });
    this.albumSingleForm.reset({ title: '', genres: [], artistIds: [], fileIndex: null });
  }

  removeAlbumSingle(i: number) { this.albumSingles.splice(i, 1); }

  // FINAL SAVE album
  async submitAlbumWizard() {
  if (!this.cover) {
    this.snack.open('Cover is required for album', 'Close', { panelClass: 'snack-error' });
    return;
  }
  if (!this.albumSingles.length) {
    this.snack.open('Add at least one single', 'Close', { panelClass: 'snack-error' });
    return;
  }
  const bad = this.albumSingles.find(s => s.fileIndex == null || !this.files[s.fileIndex]);
  if (bad) {
    this.snack.open('Each single must reference an audio file', 'Close', { panelClass: 'snack-error' });
    return;
  }

  this.isSubmittingAlbum = true;
  try {
    // 1) cover presign+PUT
    const presCover = await this.api.getPresignedUrl({
      bucketType: 'image',
      fileName: this.cover.name,
      contentType: this.cover.type || 'image/jpeg'
    }).toPromise();
    await this.api.putToS3(presCover!.url, this.cover, this.cover.type);
    const coverKey = presCover!.key;

    // 2) svaka traka presign+PUT
    const tracks = [];
    for (let i = 0; i < this.albumSingles.length; i++) {
      const s = this.albumSingles[i];
      const f = this.files[s.fileIndex];

      const presA = await this.api.getPresignedUrl({
        bucketType: 'audio',
        fileName: f.name,
        contentType: f.type || 'audio/mpeg'
      }).toPromise();
      await this.api.putToS3(presA!.url, f, f.type);

      tracks.push({
        title: s.title,
        artistIds: s.artistIds,
        genres: s.genres,
        trackNo: i + 1,
        audioKey: presA!.key
      });
    }

    // 3) POST /albums
    const payload = {
      title: this.albumForm.value.title,
      artistIds: this.albumForm.value.artistIds,
      genres: this.albumForm.value.genres,
      coverKey,
      tracks
    };

    this.api.createAlbum(payload).subscribe({
      next: () => {
        this.snack.open('Album created', 'OK', { duration: 2500 });
        this.resetAlbum();
        this.albumStep = 0;
        this.albumSingles = [];
        this.files = []; this.cover = undefined; this.coverPreview = null;
      },
      error: e => this.snack.open(e?.error?.error || e?.error?.message || 'Album failed', 'Close', { panelClass: 'snack-error' })
    });
  } catch {
    this.snack.open('Upload failed', 'Close', { panelClass: 'snack-error' });
  } finally {
    this.isSubmittingAlbum = false;
  }
}

  // async submitAlbumWizard() {
  //   if (!this.cover) {
  //     this.snack.open('Cover is required for album', 'Close', { panelClass: 'snack-error' });
  //     return;
  //   }
  //   if (!this.albumSingles.length) {
  //     this.snack.open('Add at least one single', 'Close', { panelClass: 'snack-error' });
  //     return;
  //   }
  //   const bad = this.albumSingles.find(s => s.fileIndex == null || !this.files[s.fileIndex]);
  //   if (bad) {
  //     this.snack.open('Each single must reference an audio file', 'Close', { panelClass: 'snack-error' });
  //     return;
  //   }

  //   this.isSubmittingAlbum = true;
  //   try {
  //     const coverB64 = await this.readAsB64(this.cover);
  //     const coverType = this.cover.type.split('/')[1] || 'jpg';

  //     const SongRef = await Promise.all(this.albumSingles.map(async (s, idx) => {
  //       const f = this.files[s.fileIndex];
  //       const b64 = await this.readAsB64(f);
  //       return {
  //         title: s.title,
  //         Genres: s.genres,
  //         Artists: s.artistIds,
  //         audio: b64,
  //         audioType: (f.type.split('/')[1] || 'mpeg').toLowerCase(),
  //         trackNo: idx + 1
  //       };
  //     }));

  //     const payload = {
  //       ContentType: 'ALBUM',
  //       ContentName: this.albumForm.value.title,
  //       Artists: this.albumForm.value.artistIds,
  //       Genres: this.albumForm.value.genres,
  //       image: coverB64,
  //       imageType: coverType,
  //       SongRef
  //     };

  //     this.api.createAlbum(payload).subscribe({
  //       next: () => {
  //         this.snack.open('Album created', 'OK', { duration: 2500 });
  //         this.resetAlbum();
  //         this.albumStep = 0;
  //         this.albumSingles = [];
  //         this.files = []; this.cover = undefined; this.coverPreview = null;
  //       },
  //       error: e => this.snack.open(e?.error?.error || e?.error?.message || 'Album failed', 'Close', { panelClass: 'snack-error' })
  //     }).add(() => this.isSubmittingAlbum = false);

  //   } catch {
  //     this.snack.open('Failed to read files', 'Close', { panelClass: 'snack-error' });
  //     this.isSubmittingAlbum = false;
  //   }
  // }

  // Resets
  resetSingle() {
    this.singleForm.reset({ title: '', genres: [], artistIds: [], explicit: false });
  }

  resetAlbum() {
    this.albumForm.reset({ title: '', genres: [], artistIds: [] });
    this.albumSingles = [];
    this.albumStep = 0;
  }

  // U AdminComponent.ts

// async runS3Test() {
//   if (this.singleForm.invalid || !this.files.length) {
//     this.snack.open('Choose an audio file', 'Close', { panelClass: 'snack-error' });
//     return;
//   }
//   this.isSubmittingSingle = true;
//   try {
//     const audioFile = this.files[0];
    
//     // 1. Učitaj audio fajl kao Base64 string
//     const audioB64 = await this.readAsB64(audioFile);

//     // 2. Pošalji Base64 podatke na novu Lambda funkciju
//     const uploadResult = await this.api.uploadAudioDirect({
//       audioData: audioB64,
//       fileName: audioFile.name,
//       contentType: audioFile.type || 'audio/mpeg'
//     }).toPromise();
    
//     // Opciono: Uploaduj cover sliku (može ostati pre-signed URL jer radi)
//     let imageKey: string | undefined;
//     if (this.cover) {
//       // (Ovaj kod ostaje isti kao pre)
//     }

//     // 3. Kreiraj singl u bazi sa ključem koji je vratila Lambda
//     const payload = {
//       title: this.singleForm.value.title,
//       artistIds: this.singleForm.value.artistIds,
//       genres: this.singleForm.value.genres,
//       explicit: !!this.singleForm.value.explicit,
//       audioKey: uploadResult.key, // <-- Koristimo ključ iz odgovora nove Lambde
//       ...(imageKey ? { imageKey } : {})
//     };

//     this.api.createSingle(payload).subscribe({
//       next: () => {
//         this.snack.open('Single created successfully!', 'OK', { duration: 3000 });
//         this.resetSingle();
//       },
//       error: (e) => this.snack.open(e?.error?.error || 'Failed to create single entry', 'Close', { panelClass: 'snack-error' })
//     });
    
//   } catch (e) {
//     console.error("Upload process failed:", e);
//     this.snack.open('Upload failed. Check the console.', 'Close', { panelClass: 'snack-error' });
//   } finally {
//     this.isSubmittingSingle = false;
//   }
// }
}
// implements OnInit {
//   // state
//   isSubmittingSingle = false;
//   isSubmittingAlbum  = false;

//   files: File[] = [];
//   cover?: File;
//   coverPreview?: string | ArrayBuffer | null;

//   tabIndex = 0; // 0 = single, 1 = album

//   // NEW: wizard step
//   albumStep = 0;

//   genreOptions: string[] = ['Pop','Rock','Hip-Hop','R&B','Electronic','House','Techno','Jazz','Classical','Folk','Indie','Metal'];

//   // NEW: dropdown za artiste
//   artistOptions: {id: string, name: string}[] = [
//     {id:'1', name:'Artist A'},
//     {id:'2', name:'Artist B'},
//     {id:'3', name:'Artist C'}
//   ];

//   singleForm!: FormGroup;
//   albumForm!: FormGroup;

//   // NEW: form za single unutar albuma
//   albumSingleForm!: FormGroup;

//   // NEW: kolekcija singlova za album
//   albumSingles: Array<{title:string; genres:string[]; artistIds:string[]; fileIndex:number}> = [];

//   constructor(private fb: FormBuilder, private api: UploadService, private snack: MatSnackBar) {}

//   ngOnInit() {
//     this.singleForm = this.fb.group({
//       title: ['', [Validators.required, Validators.maxLength(200)]],
//       genres: [[] as string[]],
//       artistIds: [[] as string[]],          // dropdown multiple
//       explicit: [false]
//     });

//     this.albumForm = this.fb.group({
//       title: ['', [Validators.required, Validators.maxLength(200)]],
//       genres: [[] as string[]],
//       artistIds: [[] as string[]]
//     });

//     this.albumSingleForm = this.fb.group({
//       title: ['', [Validators.required, Validators.maxLength(200)]],
//       genres: [[] as string[]],
//       artistIds: [[] as string[]],
//       fileIndex: [null, [Validators.required]]
//     });
//   }

//   // left side handlers (isti kao kod tebe)
//   onFilesSelected(ev: Event) { /* ... tvoj kod ... */ }
//   onCoverSelected(ev: Event) { /* ... tvoj kod ... */ }
//   onDragOver(e: DragEvent) { e.preventDefault(); }
//   onDrop(e: DragEvent) { /* ... tvoj kod ... */ }
//   remove(index: number) { /* ... tvoj kod ... */ }

//   // helperi
//   private readAsB64(file: File): Promise<string> {
//     return new Promise((res, rej) => {
//       const r = new FileReader();
//       r.onload = () => res((r.result as string).split(',')[1]);
//       r.onerror = rej;
//       r.readAsDataURL(file);
//     });
//   }

//   renderArtistNames(ids: string[]): string {
//     const map = new Map(this.artistOptions.map(a => [a.id, a.name]));
//     return ids.map(id => map.get(id) || id).join(', ');
//   }

//   // SINGLE SUBMIT: bez trackNo i releaseDate
//   submitSingle() {
//     if (this.singleForm.invalid || !this.files.length) {
//       this.snack.open('Choose an audio file', 'Close', { panelClass: 'snack-error' });
//       return;
//     }
//     this.isSubmittingSingle = true;

//     const audioFile = this.files[0];
//     Promise.all([
//       this.readAsB64(audioFile),
//       this.cover ? this.readAsB64(this.cover) : Promise.resolve(undefined)
//     ]).then(([audioB64, coverB64]) => {
//       const payload: any = {
//         ContentType: 'SINGLE',
//         ContentName: this.singleForm.value.title,
//         Artists: this.singleForm.value.artistIds,     // niz ID-jeva
//         Genres: this.singleForm.value.genres,
//         explicit: !!this.singleForm.value.explicit,
//         audio: audioB64,
//         audioType: audioFile.type.split('/')[1] || 'mpeg',
//         ...(coverB64 ? { image: coverB64, imageType: this.cover!.type.split('/')[1] || 'jpg' } : {})
//       };

//       this.api.createSingle(payload).subscribe({
//         next: () => {
//           this.snack.open('Single created', 'OK', { duration: 2500 });
//           this.resetSingle();
//           this.files = []; this.cover = undefined; this.coverPreview = null;
//         },
//         error: (e) => this.snack.open(e?.error?.error || e?.error?.message || 'Failed', 'Close', { panelClass:'snack-error' })
//       }).add(() => this.isSubmittingSingle = false);
//     }).catch(() => {
//       this.snack.open('Failed to read file(s)', 'Close', { panelClass: 'snack-error' });
//       this.isSubmittingSingle = false;
//     });
//   }

//   // WIZARD NAV
//   goToSingles() { this.albumStep = 1; }
//   backToAlbum() { this.albumStep = 0; }

//   // ADD single u listu
//   addAlbumSingle() {
//     if (this.albumSingleForm.invalid) return;
//     this.albumSingles.push({...this.albumSingleForm.value});
//     this.albumSingleForm.reset({ title:'', genres:[], artistIds:[], fileIndex: null });
//   }
//   removeAlbumSingle(i: number) { this.albumSingles.splice(i, 1); }

//   // FINAL SAVE album sa single-ovima
//   async submitAlbumWizard() {
//     if (!this.cover) {
//       this.snack.open('Cover is required', 'Close', { panelClass: 'snack-error' });
//       return;
//     }
//     if (!this.albumSingles.length) {
//       this.snack.open('Add at least one single', 'Close', { panelClass: 'snack-error' });
//       return;
//     }
//     // svaka stavka mora da referencira postojeći fajl
//     const bad = this.albumSingles.find(s => s.fileIndex==null || !this.files[s.fileIndex]);
//     if (bad) {
//       this.snack.open('Each single must reference an audio file', 'Close', { panelClass: 'snack-error' });
//       return;
//     }

//     this.isSubmittingAlbum = true;
//     try {
//       const coverB64 = await this.readAsB64(this.cover);
//       const coverType = this.cover.type.split('/')[1] || 'jpg';

//       const SongRef = await Promise.all(this.albumSingles.map(async (s, idx) => {
//         const f = this.files[s.fileIndex];
//         const b64 = await this.readAsB64(f);
//         return {
//           title: s.title,
//           Genres: s.genres,
//           Artists: s.artistIds,
//           audio: b64,
//           audioType: (f.type.split('/')[1] || 'mpeg').toLowerCase(),
//           trackNo: idx + 1
//         };
//       }));

//       const payload = {
//         ContentType: 'ALBUM',
//         ContentName: this.albumForm.value.title,
//         Artists: this.albumForm.value.artistIds,
//         Genres: this.albumForm.value.genres,
//         image: coverB64,
//         imageType: coverType,
//         SongRef
//       };

//       this.api.createAlbum(payload).subscribe({
//         next: () => {
//           this.snack.open('Album created', 'OK', { duration: 2500 });
//           this.resetAlbum();
//           this.albumStep = 0;
//           this.albumSingles = [];
//           this.files = []; this.cover = undefined; this.coverPreview = null;
//         },
//         error: e => this.snack.open(e?.error?.error || e?.error?.message || 'Album failed', 'Close', { panelClass: 'snack-error' })
//       }).add(() => this.isSubmittingAlbum = false);

//     } catch {
//       this.snack.open('Failed to read files', 'Close', { panelClass: 'snack-error' });
//       this.isSubmittingAlbum = false;
//     }
//   }

//   // resets
//   resetSingle() {
//     this.singleForm.reset({ title:'', genres:[], artistIds:[], explicit:false });
//   }
//   resetAlbum() {
//     this.albumForm.reset({ title:'', genres:[], artistIds:[] });
//     this.albumSingles = [];
//     this.albumStep = 0;
//   }
// }

/*
export class AdminComponent implements OnInit {
  isSubmittingSingle = false;
  isSubmittingAlbum  = false;
  selectedFile: File | null = null;

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

private fileToB64(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res((r.result as string).split(',')[1]); // bez data: prefixa
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}
submitSingle() {
  if (this.singleForm.invalid || !this.files.length) {
    this.snack.open('Choose an audio file', 'Close', { panelClass: 'snack-error' });
    return;
  }
  this.isSubmittingSingle = true;

  const audioFile = this.files[0];
  const readAsB64 = (f: File) => new Promise<string>((res, rej) => {
    const r = new FileReader();
    r.onload = () => res((r.result as string).split(',')[1]);
    r.onerror = rej;
    r.readAsDataURL(f);
  });

  Promise.all([
    readAsB64(audioFile),
    this.cover ? readAsB64(this.cover) : Promise.resolve(undefined)
  ]).then(([audioB64, coverB64]) => {

    const payload: any = {
      ContentType: 'SINGLE',
      ContentName: this.singleForm.value.title!,
      Artists: (this.singleForm.value.artistIds || '').split(',').map((s:string)=>s.trim()).filter(Boolean),
      Genres: this.singleForm.value.genres as string[],
      trackNo: Number(this.singleForm.value.trackNo) || 1,
      explicit: !!this.singleForm.value.explicit,

      // NOVO: audio
      audio: audioB64,
      audioType: audioFile.type.split('/')[1] || 'mpeg', // mpeg=mp3

      // (opciono) cover
      ...(coverB64 ? {
        image: coverB64,
        imageType: this.cover!.type.split('/')[1] || 'jpg'
      } : {})
    };

    this.api.createSingle(payload).subscribe({
      next: () => {
        this.snack.open('Single created', 'OK', { duration: 2500 });
        this.resetSingle();
        this.files = []; this.cover = undefined; this.coverPreview = null;
      },
      error: (e) => this.snack.open(e?.error?.error || e?.error?.message || 'Failed', 'Close', { panelClass:'snack-error' })
    }).add(() => this.isSubmittingSingle = false);

  }).catch(() => {
    this.snack.open('Failed to read file(s)', 'Close', { panelClass: 'snack-error' });
    this.isSubmittingSingle = false;
  });
}

submitSingleEnd() {
  if (this.singleForm.invalid || !this.cover) {
    this.snack.open('Cover image is required', 'Close', { panelClass: 'snack-error' });
    return;
  }

  this.isSubmittingSingle = true;

  const reader = new FileReader();
  reader.onload = () => {
    const base64String = (reader.result as string).split(',')[1];

    const payload = {
      ContentType: 'SINGLE',
      ContentName: this.singleForm.value.title!,
      Artists: (this.singleForm.value.artistIds || '')
                .split(',')
                .map((s: string) => s.trim())
                .filter(Boolean),
      Genres: this.singleForm.value.genres as string[],
      trackNo: Number(this.singleForm.value.trackNo) || 1,
      explicit: !!this.singleForm.value.explicit,
      image: base64String,                                // OBAVEZNO
      imageType: this.cover!.type.split('/')[1] || 'jpg'  // OBAVEZNO
    };

    this.api.createSingle(payload).subscribe({
      next: () => {
        this.snack.open('Single created', 'OK', { duration: 2500 });
        this.resetSingle();
        this.files = [];
        this.cover = undefined;
        this.coverPreview = null;
      },
      error: (e) => this.snack.open(e?.error?.error || e?.error?.message || 'Failed', 'Close', { panelClass: 'snack-error' })
    }).add(() => this.isSubmittingSingle = false);
  };

  reader.onerror = () => {
    this.snack.open('Failed to read cover image', 'Close', { panelClass: 'snack-error' });
    this.isSubmittingSingle = false;
  };

  reader.readAsDataURL(this.cover!);
}

// helper za čitanje fajla kao base64 (bez data: prefixa)
private readAsB64(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res((r.result as string).split(',')[1]);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}

submitAlbum() {
  if (this.albumForm.invalid || !this.cover || !this.files.length) {
    this.snack.open('Cover i bar jedan audio su obavezni', 'Close', { panelClass: 'snack-error' });
    return;
  }

  this.isSubmittingAlbum = true;

  const readAsB64 = (f: File) => new Promise<string>((res, rej) => {
    const r = new FileReader();
    r.onload = () => res((r.result as string).split(',')[1]);
    r.onerror = rej;
    r.readAsDataURL(f);
  });

  // 1) Učitaj cover → b64
  readAsB64(this.cover!)
    // 2) Učitaj sve audio fajlove → niz objekata
    .then(coverB64 => {
      const coverType = this.cover!.type.split('/')[1] || 'jpg';
      return Promise.all(
        this.files.map((f, i) =>
          readAsB64(f).then(b64 => ({
            title: f.name.replace(/\.[^.]+$/, '') || `track-${i + 1}`,
            audio: b64,
            audioType: (f.type.split('/')[1] || 'mpeg').toLowerCase()
          }))
        )
      ).then(SongRef => ({ coverB64, coverType, SongRef }));
    })
    // 3) Pošalji payload
    .then(({ coverB64, coverType, SongRef }) => {
      const payload = {
        ContentType: 'ALBUM',
        ContentName: this.albumForm.value.title!,
        Artists: (this.albumForm.value.artistIds || '')
                  .split(',').map((s: string) => s.trim()).filter(Boolean),
        Genres: this.albumForm.value.genres as string[],
        releaseYear: this.albumForm.value.releaseYear || null,
        image: coverB64,
        imageType: coverType,
        SongRef // niz { title, audio, audioType }
      };

      this.api.createAlbum(payload).subscribe({
        next: () => {
          this.snack.open('Album created', 'OK', { duration: 2500 });
          this.resetAlbum();
          this.files = []; this.cover = undefined; this.coverPreview = null;
        },
        error: e =>
          this.snack.open(e?.error?.error || e?.error?.message || 'Album failed', 'Close', { panelClass: 'snack-error' })
      }).add(() => (this.isSubmittingAlbum = false));
    })
    // 4) Greške pri čitanju fajlova
    .catch(() => {
      this.snack.open('Failed to read files', 'Close', { panelClass: 'snack-error' });
      this.isSubmittingAlbum = false;
    });
}

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

}
*/