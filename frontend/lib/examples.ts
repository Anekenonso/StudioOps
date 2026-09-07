import type { ResearchDraft } from './draft'

/**
 * The example pills from the UI spec. Each one fills the whole draft so a judge
 * can run a credible research pass in a single click.
 */
export interface Example {
  label: string
  draft: ResearchDraft
}

export const EXAMPLES: Example[] = [
  {
    label: 'Nigerian crime thriller',
    draft: {
      description:
        "We're developing a Nigerian crime thriller set in Lagos. Research the current market, comparable films, audience trends, potential locations, distribution opportunities, and relevant production companies.",
      title: 'Lagos After Dark',
      format: 'Feature Film',
      genre: 'Crime Thriller',
      geography: 'Nigeria',
      audience: 'Adults 18-34',
      questions:
        'Which recent Nollywood crime titles performed well internationally?\nWhich platforms are commissioning Nigerian scripted drama?',
    },
  },
  {
    label: 'Afrobeats documentary',
    draft: {
      description:
        'We are producing a feature documentary on the global rise of Afrobeats, following artists across Lagos, London, and Atlanta. Research the documentary market, comparable music docs, audience appetite, festival routes, and streaming buyers.',
      title: 'Afrobeats: The Global Takeover',
      format: 'Documentary',
      genre: 'Music Documentary',
      geography: 'Nigeria, United Kingdom, United States',
      audience: 'Music fans 18-40',
      questions:
        'Which music documentaries have sold well to streamers recently?\nWhich festivals launch music documentaries most effectively?',
    },
  },
  {
    label: 'Sci-fi series in Africa',
    draft: {
      description:
        'We are developing an eight-episode science fiction series set in a near-future East African megacity, exploring climate migration and AI governance. Research the market for African genre television, comparable series, VFX and production capacity, co-production funding, and buyer appetite.',
      title: 'Nairobi 2085',
      format: 'TV Series',
      genre: 'Science Fiction',
      geography: 'Kenya',
      audience: 'Genre viewers 18-44',
      questions:
        'Which African genre series have been commissioned in the last three years?\nWhat co-production funding exists for East African drama?',
    },
  },
  {
    label: 'Coming-of-age drama',
    draft: {
      description:
        'We are financing a coming-of-age drama about a teenage swimmer in a coastal South African town. Research the arthouse and festival market, comparable titles, audience trends for youth drama, regional incentives, and distribution routes.',
      title: 'Salt Water',
      format: 'Feature Film',
      genre: 'Coming-of-Age Drama',
      geography: 'South Africa',
      audience: 'Festival and arthouse audiences',
      questions:
        'Which recent coming-of-age dramas found distribution after a festival premiere?\nWhat production incentives apply to filming in the Western Cape?',
    },
  },
]
