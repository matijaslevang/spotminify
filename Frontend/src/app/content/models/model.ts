export interface Artist {
    artistId?: any;
    name: string,
    biography: string,
    genres: string[],
    imageUrl: string
}

export interface Song {
    songId?: any;
    name: string,
    artists: string[],
    genres: string[],
    imageUrl: string,
    songUrl: string,
    rating: number,
}

export interface Album {
    albumId?: any;
    name: string,
    artists: string[],
    genres: string[],
    imageUrl: string,
    songsUrls: string[],
    rating: number,
}

export interface Genre {
  genreId: string;
  genreName: string;
}

export interface FilterDetails {
    contentName: string,
    contentId: string,
    imageUrl: string,
    contentGenres: string[],
    contentArtists?: string[]
}