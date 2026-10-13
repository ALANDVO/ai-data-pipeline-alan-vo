import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import Quality from '../pages/Quality'
import Jobs from '../pages/Jobs'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    quality: vi.fn(),
    jobs: vi.fn(),
  },
}))

const mockQualityScores = [
  {
    pipeline_id: 'pipe-1',
    dataset: 'orders',
    completeness: 0.94,
    accuracy: 0.97,
    consistency: 0.92,
    timeliness: 0.88,
    overall: 0.93,
    issues: ['3.2% null values in email field'],
    scored_at: Date.now() / 1000 - 3600,
  },
  {
    pipeline_id: 'pipe-2',
    dataset: 'logs',
    completeness: 0.87,
    accuracy: 0.91,
    consistency: 0.85,
    timeliness: 0.95,
    overall: 0.90,
    issues: ['230 malformed log entries'],
    scored_at: Date.now() / 1000 - 1800,
  },
]

const mockJobs = [
  {
    id: 'job-1',
    pipeline_id: 'pipe-1',
    status: 'completed',
    triggered_by: 'user',
    started_at: Date.now() / 1000 - 7200,
    completed_at: Date.now() / 1000 - 7100,
    duration_ms: 10000,
    tasks: [
      { task_id: 'task-1', status: 'completed', rows_processed: 100, duration_ms: 5000, error: null, retries: 0, output: {} },
    ],
    error: null,
  },
  {
    id: 'job-2',
    pipeline_id: 'pipe-2',
    status: 'failed',
    triggered_by: 'schedule',
    started_at: Date.now() / 1000 - 3600,
    completed_at: Date.now() / 1000 - 3550,
    duration_ms: 5000,
    tasks: [
      { task_id: 'task-1', status: 'failed', rows_processed: 0, duration_ms: 2000, error: 'Connection timeout', retries: 3, output: {} },
    ],
    error: 'Connection timeout',
  },
]

describe('Quality Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.quality.mockResolvedValue(mockQualityScores)
  })

  it('renders quality scores and summary stats', async () => {
    render(<BrowserRouter><Quality /></BrowserRouter>)

    await waitFor(() => {
      expect(screen.getByText('Data Quality')).toBeInTheDocument()
    })

    // "2" appears twice: Datasets Scored and Critical Issues
    expect(screen.getAllByText('2')).toHaveLength(2)
    expect(screen.getByText('91.5%')).toBeInTheDocument() // Average Overall
    // Each item shows "1 issues" (not "2 issues")
    expect(screen.getAllByText('1 issues')).toHaveLength(2)

    expect(screen.getByText('pipe-1')).toBeInTheDocument()
    expect(screen.getByText('orders')).toBeInTheDocument()
    expect(screen.getByText('pipe-2')).toBeInTheDocument()
    expect(screen.getByText('logs')).toBeInTheDocument()
  })

  it('shows detail view when a score is selected', async () => {
    render(<BrowserRouter><Quality /></BrowserRouter>)

    await waitFor(() => {
      expect(screen.getByText('pipe-1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('pipe-1'))

    await waitFor(() => {
      expect(screen.getByText('orders — pipe-1')).toBeInTheDocument()
      expect(screen.getByText('Completeness')).toBeInTheDocument()
      expect(screen.getByText('94.0%')).toBeInTheDocument()
      expect(screen.getByText('Accuracy')).toBeInTheDocument()
      expect(screen.getByText('97.0%')).toBeInTheDocument()
      expect(screen.getByText('3.2% null values in email field')).toBeInTheDocument()
    })
  })

  it('shows empty state when no scores', async () => {
    api.quality.mockResolvedValue([])
    render(<BrowserRouter><Quality /></BrowserRouter>)

    await waitFor(() => {
      expect(screen.getByText('No quality scores yet.')).toBeInTheDocument()
    })
  })
})

describe('Jobs Page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    api.jobs.mockResolvedValue(mockJobs)
  })

  it('renders job list with status badges', async () => {
    render(<BrowserRouter><Jobs /></BrowserRouter>)

    await waitFor(() => {
      expect(screen.getByText('Job History')).toBeInTheDocument()
    })

    expect(screen.getByText('job-1')).toBeInTheDocument()
    expect(screen.getByText('job-2')).toBeInTheDocument()
    // Status badges render capitalized (also in dropdown, so use getAllByText)
    expect(screen.getAllByText('Completed')).toHaveLength(2)
    expect(screen.getAllByText('Failed')).toHaveLength(2)
    // Pipeline IDs only shown in expanded detail view
  })

  it('expands job details on click', async () => {
    render(<BrowserRouter><Jobs /></BrowserRouter>)

    await waitFor(() => {
      expect(screen.getByText('job-1')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('job-1'))

    await waitFor(() => {
      expect(screen.getByText('task-1')).toBeInTheDocument()
      // Table cell shows "100" not "100 rows"
      expect(screen.getByText('100')).toBeInTheDocument()
      expect(screen.getByText('5.00s')).toBeInTheDocument()
    })
  })

  it('shows retry button for failed jobs', async () => {
    render(<BrowserRouter><Jobs /></BrowserRouter>)

    await waitFor(() => {
      expect(screen.getByText('job-2')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('job-2'))

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /retry/i })).toBeInTheDocument()
    })
  })
})