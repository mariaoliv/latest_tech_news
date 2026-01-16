import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

interface NewsSummaryResponse {
    summary: string
    error?: string
}

export const getNewsSummary = async () : Promise<string> => {
    try {
        const response = await client.get<NewsSummaryResponse>('/news_summary')
        return response.data.summary
    }
    catch(error) {
        console.error("Error fetching news summary: ", error)
        throw(error)
    }
}