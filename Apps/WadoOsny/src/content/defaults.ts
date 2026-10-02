export type ClubLocation = {
  name: string;
  address: string;
  city: string;
  short: string;
  mapsUrl: string;
};

export type ClubInfo = {
  name: string;
  fullName: string;
  tagline: string;
  email: string;
  association: string;
  rna: string;
  siege: string;
  mapImage: string;
  mapLink: string;
  locations: ClubLocation[];
};

export type GalleryItem = {
  id: string;
  src: string;
  alt: string;
  category: string;
};

export type Instructor = {
  id: string;
  name: string;
  image: string;
  ranks: string[];
  bio: string;
};

export type ScheduleSlot = {
  day: string;
  time: string;
  place: string;
};

export type KidsGroup = {
  id: string;
  group: string;
  ages: string;
  focus: string;
  slots: ScheduleSlot[];
};

export type AdultGroup = {
  id: string;
  title: string;
  description: string;
  slots: ScheduleSlot[];
};

export type Schedules = {
  kids: KidsGroup[];
  adults: AdultGroup[];
};

export type PricingPlan = {
  id: string;
  title: string;
  club: number;
  license: number | null;
  note: string;
};

export type ClubEvent = {
  id: string;
  title: string;
  date: string;
  time: string;
  place: string;
  description: string;
};

export const defaultClub: ClubInfo = {
  name: "Wado-Osny",
  fullName: "Karaté Wado Ryu Osny",
  tagline: "Club de karaté en Île-de-France",
  email: "wado.osny@gmail.com",
  association: "Association Sportive Karaté Osny",
  rna: "W953008150",
  siege: "47 avenue Roger Guichard, 95610 Éragny-sur-Oise",
  mapImage: "/images/plan-acces.jpg",
  mapLink:
    "https://www.google.com/maps/search/?api=1&query=Dojo+municipal+Stade+Christian+Léon+Rue+de+Chars+95520+Osny",
  locations: [
    {
      name: "Dojo municipal du Stade Christian Léon",
      address: "Rue de Chars",
      city: "95520 Osny",
      short: "Dojo",
      mapsUrl:
        "https://www.google.com/maps/search/?api=1&query=Dojo+municipal+Stade+Christian+Léon+Rue+de+Chars+95520+Osny",
    },
    {
      name: "Salle de Motricité, École Maternelle Yves Le Guern",
      address: "(Adresse proche de l’entrée parking) 31 rue Jean Jaurès",
      city: "95520 Osny",
      short: "École Yves Le Guern",
      mapsUrl:
        "https://www.google.com/maps/search/?api=1&query=31+rue+Jean+Jaurès+95520+Osny",
    },
  ],
};

export const defaultGallery: GalleryItem[] = [
  {
    id: "g1",
    src: "/images/mediatheque/photo-groupe-stage-1.jpg",
    alt: "Groupe stage — photo 1",
    category: "Stages",
  },
  {
    id: "g2",
    src: "/images/mediatheque/photo-groupe-stage-2.jpg",
    alt: "Groupe stage — photo 2",
    category: "Stages",
  },
  {
    id: "g3",
    src: "/images/mediatheque/photo-groupe-stage-3.jpg",
    alt: "Groupe stage — photo 3",
    category: "Stages",
  },
  {
    id: "g4",
    src: "/images/mediatheque/photo-cours-karate-1.jpg",
    alt: "Cours de karaté — photo 1",
    category: "Cours",
  },
  {
    id: "g5",
    src: "/images/mediatheque/photo-cours-karate-2.jpg",
    alt: "Cours de karaté — photo 2",
    category: "Cours",
  },
  {
    id: "g6",
    src: "/images/mediatheque/photo-cours-karate-3.jpg",
    alt: "Cours de karaté — photo 3",
    category: "Cours",
  },
  {
    id: "g7",
    src: "/images/mediatheque/photo-tobin-threadgill.jpg",
    alt: "Toby Threadgill — TSYR",
    category: "TSYR",
  },
  {
    id: "g8",
    src: "/images/mediatheque/photo-cours-karate-handi.jpg",
    alt: "Cours de karaté inclusif",
    category: "Cours",
  },
  {
    id: "g9",
    src: "/images/mediatheque/photo-groupe-stage-enfants-1.jpg",
    alt: "Stage enfants — photo 1",
    category: "Enfants",
  },
  {
    id: "g10",
    src: "/images/mediatheque/photo-groupe-stage-enfants-2.jpg",
    alt: "Stage enfants — photo 2",
    category: "Enfants",
  },
  {
    id: "g11",
    src: "/images/mediatheque/photo-groupe-stage-enfants-3.jpg",
    alt: "Stage enfants — photo 3",
    category: "Enfants",
  },
];

export const defaultInstructors: Instructor[] = [
  {
    id: "anthony-gilson",
    name: "Anthony Gilson",
    image: "/images/anthony-gilson.jpg",
    ranks: [
      "3e DAN FFK Wado Ryu",
      "Diplôme d’Instructeur Fédéral FFK et CQP",
      "Instructeur Shoden TSYR",
    ],
    bio: "Débute le karaté en 1999 à Osny dans le Val d’Oise. Passe sa ceinture noire 1er dan ainsi que son DIF en 2010. Commence la pratique du TSYR en 2012 sous l’instruction de Nicolas Delalondre Sensei. Quelques années après, prend la charge d’instructeur principal du club et devient par la suite élève de Minh Tran Hieu Sensei en Wado Ryu. En 2022, reçoit le niveau d’instructeur Shoden de TSYR.",
  },
  {
    id: "anne-cecile-bigattin",
    name: "Anne-Cécile Bigattin",
    image: "/images/anne-cecile-bigattin.jpg",
    ranks: [
      "3e DAN FFK Wado Ryu",
      "Diplôme d’Instructeur Fédéral FFK et CQP",
      "Présidente du club",
    ],
    bio: "Débute le karaté Wado Ryu en 1996 avec Babette Biais Sensei à Bondy. Passe sa ceinture noire ainsi que son DIF en 2006. Arrive au dojo d’Osny en 2019, intègre l’équipe d’enseignants et prend en charge la présidence du club dans les années qui suivent.",
  },
  {
    id: "daniele-valli",
    name: "Daniele Valli",
    image: "/images/daniele-valli.jpg",
    ranks: [
      "2e DAN Wado Academy",
      "1er DAN FFK Wado Ryu",
      "Diplôme d’Assistant Fédéral FFK",
      "Instructeur Shoden TSYR",
    ],
    bio: "Débute le karaté en 1996 en Italie à Rome. Pratique les arts martiaux chinois pendant une dizaine d’années avant de se consacrer uniquement au karaté en 2005. En 2009, rencontre Minh Tran Hieu Sensei et arrive en France en 2011. Débute le TSYR en 2016 aux USA avant de rentrer en France. Passe sa ceinture noire Wado Academy en 2014 et son deuxième dan en 2020. Devient Instructeur TSYR Shoden en 2021. Passe son 1er dan FFK en 2022.",
  },
];

export const defaultSchedules: Schedules = {
  kids: [
    {
      id: "petits",
      group: "Petits",
      ages: "5–6 ans",
      focus: "Motricité et découverte des principes fondamentaux du karaté.",
      slots: [
        { day: "Mardi", time: "17h30–18h15", place: "Dojo" },
        { day: "Mercredi", time: "14h00–15h00", place: "École Yves Le Guern" },
        { day: "Jeudi", time: "17h30–18h15", place: "Dojo" },
      ],
    },
    {
      id: "moyens",
      group: "Moyens",
      ages: "7–9 ans",
      focus: "Karaté traditionnel et initiation au karaté compétitif.",
      slots: [
        { day: "Mardi", time: "18h15–19h00", place: "Dojo" },
        { day: "Mercredi", time: "15h00–16h00", place: "École Yves Le Guern" },
        { day: "Jeudi", time: "18h15–19h00", place: "Dojo" },
      ],
    },
    {
      id: "grands",
      group: "Grands",
      ages: "9–12 ans",
      focus: "Spécificités du style Wado Ryu et préparation aux compétitions.",
      slots: [
        { day: "Mardi", time: "19h00–20h00", place: "Dojo" },
        { day: "Mercredi", time: "16h00–17h00", place: "École Yves Le Guern" },
        { day: "Jeudi", time: "19h00–20h00", place: "Dojo" },
      ],
    },
  ],
  adults: [
    {
      id: "wado-ryu",
      title: "Wado Ryu",
      description:
        "Découverte et approfondissement des principes du karaté Wado Ryu.",
      slots: [
        { day: "Mardi", time: "20h00–22h00", place: "École Yves Le Guern" },
        { day: "Mercredi", time: "19h00–21h00", place: "École Yves Le Guern" },
        { day: "Jeudi", time: "20h00–22h00", place: "École Yves Le Guern" },
      ],
    },
    {
      id: "self-defense",
      title: "Self-défense",
      description: "Gestion de situations conflictuelles dans le cadre légal.",
      slots: [
        { day: "Mardi", time: "21h00–22h00", place: "École Yves Le Guern" },
      ],
    },
    {
      id: "karate-contact",
      title: "Karaté contact",
      description: "Percussions pieds/poings et mises au sol.",
      slots: [
        { day: "Jeudi", time: "21h00–22h00", place: "École Yves Le Guern" },
      ],
    },
    {
      id: "tsyr",
      title: "TSYR",
      description:
        "École d’armes et de jujutsu, origine des principes du Wado Ryu.",
      slots: [
        { day: "Vendredi", time: "19h30–21h30", place: "École Yves Le Guern" },
        { day: "Samedi", time: "9h00–11h00", place: "École Yves Le Guern" },
      ],
    },
  ],
};

export const defaultPricing: PricingPlan[] = [
  {
    id: "enfants",
    title: "Cours enfants",
    club: 150,
    license: 37,
    note: "Licence fédérale FFK en option / obligatoire selon pratique.",
  },
  {
    id: "ados-adultes",
    title: "Cours ados / adultes",
    club: 180,
    license: 37,
    note: "Wado Ryu — cotisation annuelle du club.",
  },
  {
    id: "self-contact",
    title: "Self-défense / Karaté contact",
    club: 180,
    license: null,
    note: "Cours ados / adultes.",
  },
];

export const defaultEvents: ClubEvent[] = [
  {
    id: "ev-2024-08-20",
    title: "Cours de Self Defense",
    date: "2024-08-20",
    time: "20h00 – 22h00",
    place: "Salle de Motricité — 31 rue Jean Jaurès, Osny",
    description:
      "Focus sur la gestion de situations conflictuelles dans le cadre légal.",
  },
  {
    id: "ev-2024-08-07",
    title: "Cours de karaté Wado Ryu (7–9 ans)",
    date: "2024-08-07",
    time: "18h15 – 19h00",
    place: "Dojo — Rue de Chars, Osny",
    description:
      "Découverte plus appuyée de la pratique du karaté sous forme traditionnelle et initiation au karaté compétitif.",
  },
  {
    id: "ev-2024-08-03",
    title: "Cours de TSYR (Adultes)",
    date: "2024-08-03",
    time: "9h00 – 11h00",
    place: "Salle de Motricité — 31 rue Jean Jaurès, Osny",
    description:
      "Découverte et approfondissement d’une ancienne école d’arme et de jujutsu, origine des principes du Wado Ryu.",
  },
];

export const GALLERY_CATEGORIES = ["Stages", "Cours", "Enfants", "TSYR"] as const;
