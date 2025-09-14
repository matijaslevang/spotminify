export interface Artist {
    name: string,
    bio: string,
    genres: string[],
    imageUrl: string
}

export interface Song {
    name: string,
    artists: string[],
    genres: string[],
    imageUrl: string,
    songUrl: string,
    rating: number,
}

export interface Album {
    name: string,
    artists: string[],
    genres: string[],
    imageUrl: string,
    songsUrls: string[],
    rating: number,
}