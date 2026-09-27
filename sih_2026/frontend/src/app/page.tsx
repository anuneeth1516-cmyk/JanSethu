"use client";

import { useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Bot,
  Building2,
  Camera,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleHelp,
  Compass,
  Eye,
  EyeOff,
  Factory,
  FileText,
  Globe2,
  GraduationCap,
  Landmark,
  LogIn,
  LogOut,
  MapPin,
  Menu,
  MessageCircle,
  Navigation,
  Plus,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  ThumbsUp,
  Users,
  UsersRound,
  Video,
  Waypoints,
  X,
} from "lucide-react";

type Problem = {
  id: string;
  title: string;
  place: string;
  severity: string;
  reports: number;
  tags: string[];
  progress: number;
  status: string;
  x: number;
  y: number;
  latitude?: number | null;
  longitude?: number | null;
  description?: string;
  media_url?: string | null;
  media_type?: "image" | "video" | null;
  distance_km?: number | null;
  analysis?: {
    summary: string;
    severity: string;
    urgency: string;
    required_skills: string[];
    required_expertise: string[];
    required_resources: string[];
    tags: string[];
  };
  matches?: Match[];
};

type CollaboratorProfile = {
  candidate_id: string;
  name: string;
  role: string;
  email?: string | null;
  phone?: string | null;
  organization?: string | null;
  organization_type?: string | null;
  location?: string | null;
  skills: string[];
  expertise: string[];
  resources: string[];
  technologies: string[];
};

type Match = CollaboratorProfile & {
  matching_skills: string[];
  score: number;
  explanation: string;
  availability?: string | null;
};

type CollaborationRequest = {
  id: string;
  problem_id: string;
  requester_id: string;
  recipient_id: string;
  status: "pending" | "accepted" | "rejected" | "cancelled";
  message: string;
  created_at: string;
  updated_at: string;
  collaborator?: CollaboratorProfile | null;
};

type AuthUser = {
  id: string;
  email: string;
  role: string;
  profile?: { display_name: string; location_text?: string };
};

function getFullMediaUrl(url?: string | null): string {
  if (!url) return "";
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  const backendBase = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1").replace(/\/api\/v1\/?$/, "");
  return `${backendBase}${url.startsWith("/") ? "" : "/"}${url}`;
}

function calculateHaversineDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) * Math.cos((lat2 * Math.PI) / 180) * Math.sin(dLon / 2) * Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Math.round(R * c * 10) / 10;
}

function problemFromApi(value: any, userLat?: number | null, userLng?: number | null): Problem {
  const analysis = value.analysis;
  const meta = value.metadata || {};
  const lat = typeof value.latitude === "number" ? value.latitude : null;
  const lng = typeof value.longitude === "number" ? value.longitude : null;

  let distance: number | null = null;
  if (typeof value.location?.distance_km === "number") {
    distance = value.location.distance_km;
  } else if (typeof meta.distance_km === "number") {
    distance = meta.distance_km;
  } else if (userLat != null && userLng != null && lat != null && lng != null) {
    distance = calculateHaversineDistance(userLat, userLng, lat, lng);
  }

  return {
    id: value.id,
    title: value.title,
    place: value.location_text || "Location pending",
    severity: analysis?.severity || "Medium",
    reports: value.report_count ?? 1,
    tags: analysis?.tags || [],
    progress: 4,
    status: value.status || "Reported",
    x: 56,
    y: 44,
    latitude: lat,
    longitude: lng,
    description: value.description || value.summary || "",
    media_url: value.media_url || meta.media_url || null,
    media_type: value.media_type || meta.media_type || null,
    distance_km: distance,
    analysis,
    matches: value.matches || [],
  };
}

function escapeMapHtml(value: string): string {
  return value.replace(/[&<>'"]/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[character] || character);
}

// Interactive Map Pin Selector (like Rapido/Uber)
function LocationPickerMap({
  initialLat,
  initialLng,
  onLocationSelect,
}: {
  initialLat?: number | null;
  initialLng?: number | null;
  onLocationSelect: (lat: number, lng: number) => void;
}) {
  const hostRef = useRef<HTMLDivElement>(null);
  const markerRef = useRef<any>(null);

  useEffect(() => {
    let disposed = false;
    let map: any = null;
    const startLat = initialLat && Number.isFinite(initialLat) ? initialLat : 17.385;
    const startLng = initialLng && Number.isFinite(initialLng) ? initialLng : 78.4867;

    void import("leaflet").then(({ default: L }) => {
      const host = hostRef.current;
      if (disposed || !host || !host.isConnected) return;
      host.replaceChildren();

      map = L.map(host, { zoomControl: true, scrollWheelZoom: true }).setView([startLat, startLng], 14);
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "&copy; OpenStreetMap contributors",
        maxZoom: 19,
      }).addTo(map);

      const pinIcon = L.divIcon({
        className: "picker-pin-icon",
        html: `<div style="background:#f18d48;color:white;width:34px;height:34px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);display:grid;place-items:center;border:3px solid white;box-shadow:0 4px 10px rgba(0,0,0,0.35);"><span style="transform:rotate(45deg);font-size:15px;">📍</span></div>`,
        iconSize: [34, 34],
        iconAnchor: [17, 34],
      });

      const marker = L.marker([startLat, startLng], { icon: pinIcon, draggable: true }).addTo(map);
      markerRef.current = marker;

      marker.on("dragend", () => {
        const pos = marker.getLatLng();
        onLocationSelect(pos.lat, pos.lng);
      });

      map.on("click", (e: any) => {
        marker.setLatLng(e.latlng);
        onLocationSelect(e.latlng.lat, e.latlng.lng);
      });

      window.setTimeout(() => {
        if (!disposed && host.isConnected && map) {
          map.invalidateSize(true);
        }
      }, 150);
    });

    return () => {
      disposed = true;
      map?.remove();
    };
  }, []);

  return <div ref={hostRef} style={{ width: "100%", height: 260, borderRadius: 8, overflow: "hidden", position: "relative" }} />;
}

// Display Map Component
function LeafletMap({
  problems,
  onSelect,
  centerCoords,
  emptyText,
}: {
  problems: Problem[];
  onSelect: (problem: Problem) => void;
  centerCoords?: { lat: number; lng: number } | null;
  emptyText?: string;
}) {
  const hostRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let disposed = false;
    let map: { remove: () => void; invalidateSize: (animate?: boolean) => void } | null = null;
    const validProblems = problems.filter((problem) => Number.isFinite(problem.latitude) && Number.isFinite(problem.longitude));

    void import("leaflet").then(({ default: L }) => {
      const host = hostRef.current;
      if (disposed || !host || !host.isConnected) return;

      host.replaceChildren();
      const leafletMap = L.map(host, { zoomControl: true, scrollWheelZoom: true });
      map = leafletMap;
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap contributors", maxZoom: 19 }).addTo(leafletMap);

      if (centerCoords && Number.isFinite(centerCoords.lat) && Number.isFinite(centerCoords.lng)) {
        const centerIcon = L.divIcon({
          className: "center-marker-pin",
          html: `<div style="background:#176b61;color:white;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;font-size:16px;border:3px solid white;box-shadow:0 4px 10px rgba(0,0,0,0.3);">🎓</div>`,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
        });
        const centerMarker = L.marker([centerCoords.lat, centerCoords.lng], { icon: centerIcon }).addTo(leafletMap);
        centerMarker.bindPopup("<strong>University Campus / Base Location</strong>");
      }

      const markers = validProblems.map((problem) => {
        const marker = L.marker([problem.latitude as number, problem.longitude as number]).addTo(leafletMap);
        const mediaHtml = problem.media_url
          ? problem.media_type === "video"
            ? `<video src="${getFullMediaUrl(problem.media_url)}" style="width:100%;max-height:120px;border-radius:6px;margin:6px 0;" controls></video>`
            : `<img src="${getFullMediaUrl(problem.media_url)}" alt="${escapeMapHtml(problem.title)}" style="width:100%;max-height:120px;object-fit:cover;border-radius:6px;margin:6px 0;" />`
          : "";

        marker.bindPopup(
          `<strong>${escapeMapHtml(problem.title)}</strong><br />${escapeMapHtml(problem.place)}<br /><small>${escapeMapHtml(problem.severity)} · ${problem.reports} reports</small>${mediaHtml}<p style="margin:4px 0 8px;">${escapeMapHtml((problem.description || "").slice(0, 140))}</p><button type="button" data-problem-id="${escapeMapHtml(problem.id)}" style="background:#176b61;color:white;border:none;padding:5px 10px;border-radius:5px;cursor:pointer;font-size:11px;">View details</button>`
        );
        marker.on("popupopen", () => {
          const button = host.querySelector<HTMLButtonElement>(`button[data-problem-id="${problem.id}"]`);
          button?.addEventListener("click", () => onSelect(problem));
        });
        return marker;
      });

      if (markers.length) {
        leafletMap.fitBounds(L.latLngBounds(markers.map((marker) => marker.getLatLng())).pad(0.2), { maxZoom: 13 });
      } else if (centerCoords) {
        leafletMap.setView([centerCoords.lat, centerCoords.lng], 12);
      } else {
        leafletMap.setView([20.5937, 78.9629], 5);
        const empty = document.createElement("div");
        empty.className = "map-empty-overlay";
        empty.textContent = emptyText || "No reported events on the map yet.";
        host.appendChild(empty);
      }

      window.setTimeout(() => {
        if (disposed || !host.isConnected || !leafletMap || !map) return;
        try {
          leafletMap.invalidateSize(true);
        } catch (error) {
          console.warn("Map resize skipped.", error);
        }
      }, 100);
    });

    return () => {
      disposed = true;
      map?.remove();
      map = null;
    };
  }, [problems, onSelect, centerCoords, emptyText]);

  return <div ref={hostRef} className="leaflet-host" />;
}

export default function Home() {
  const [allProblems, setAllProblems] = useState<Problem[]>([]);
  const [myReports, setMyReports] = useState<Problem[]>([]);
  const [activeNav, setActiveNav] = useState("Overview");
  const [showReport, setShowReport] = useState(false);
  const [selected, setSelected] = useState<Problem | null>(null);
  const [problemsLoading, setProblemsLoading] = useState(true);

  // Report creation state
  const [reportDescription, setReportDescription] = useState("");
  const [reportLocation, setReportLocation] = useState("");
  const [reportLatitude, setReportLatitude] = useState<number | null>(null);
  const [reportLongitude, setReportLongitude] = useState<number | null>(null);
  const [locatingUser, setLocatingUser] = useState(false);
  const [showMapPicker, setShowMapPicker] = useState(false);
  const [mediaFile, setMediaFile] = useState<File | null>(null);
  const [mediaPreviewUrl, setMediaPreviewUrl] = useState<string | null>(null);
  const [mediaType, setMediaType] = useState<"image" | "video" | null>(null);
  const [reportError, setReportError] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [reportSubmitting, setReportSubmitting] = useState(false);
  const [notice, setNotice] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Matches and Chat
  const [matches, setMatches] = useState<Match[]>([]);
  const [matchesLoading, setMatchesLoading] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState([
    { role: "assistant", text: "Hi! I’m here to help you report an event or connect with universities and collaborators." },
  ]);

  // Auth state
  const [currentUser, setCurrentUser] = useState<AuthUser | null>(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [authRole, setAuthRole] = useState("student");
  const [authError, setAuthError] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [passwordVisible, setPasswordVisible] = useState(false);

  // Collaborations
  const [collaborationRequests, setCollaborationRequests] = useState<CollaborationRequest[]>([]);
  const [collaborationLoading, setCollaborationLoading] = useState(false);
  const [collaborationError, setCollaborationError] = useState("");
  const [collaborationSending, setCollaborationSending] = useState<Record<string, boolean>>({});
  const [myReportMatches, setMyReportMatches] = useState<Record<string, Match[]>>({});
  const [myReportsLoading, setMyReportsLoading] = useState(false);
  const [myReportsError, setMyReportsError] = useState("");

  // Support tracking
  const [supportingProblem, setSupportingProblem] = useState<Record<string, boolean>>({});
  const [supportedMap, setSupportedMap] = useState<Record<string, boolean>>({});

  // University Interface filters & location
  const [universityLocation, setUniversityLocation] = useState<{ lat: number; lng: number; name: string }>({
    lat: 17.385,
    lng: 78.4867,
    name: "Hyderabad Tech Campus",
  });
  const [universityRadiusKm, setUniversityRadiusKm] = useState<number>(25);
  const [universityDisciplineFilter, setUniversityDisciplineFilter] = useState<string>("all");

  const displayName = currentUser?.profile?.display_name || currentUser?.email?.split("@")[0] || "there";

  // Strict role check: citizen/student gets ONLY citizen/student interface; university gets university interface!
  const isUniversity = currentUser?.role?.toLowerCase() === "university" || currentUser?.role?.toLowerCase() === "researcher";

  const showNotice = (message: string) => {
    setNotice(message);
    window.setTimeout(() => setNotice(""), 4000);
  };

  // Rapido-style Location Option 1: Current GPS location
  const detectLocation = () => {
    if (typeof window === "undefined" || !navigator.geolocation) {
      showNotice("Geolocation is not supported by your browser.");
      return;
    }
    setLocatingUser(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        setReportLatitude(lat);
        setReportLongitude(lng);

        try {
          const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`, {
            headers: { "Accept-Language": "en" },
          });
          if (res.ok) {
            const data = await res.json();
            const address = data.address || {};
            const suburb = address.suburb || address.neighbourhood || address.city_district || "";
            const city = address.city || address.town || address.county || address.state || "";
            const placeStr = [suburb, city].filter(Boolean).join(", ") || data.display_name.split(",").slice(0, 3).join(",");
            setReportLocation(placeStr || `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
          } else {
            setReportLocation(`${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`);
          }
        } catch {
          setReportLocation(`${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`);
        } finally {
          setLocatingUser(false);
          showNotice("Current location captured!");
        }
      },
      (err) => {
        setLocatingUser(false);
        showNotice(`Location access denied or unavailable: ${err.message}`);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  };

  // Rapido-style Location Option 2: Pick on Map
  const handleLocationPicked = async (lat: number, lng: number) => {
    setReportLatitude(lat);
    setReportLongitude(lng);
    try {
      const res = await fetch(`https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lng}`, {
        headers: { "Accept-Language": "en" },
      });
      if (res.ok) {
        const data = await res.json();
        const address = data.address || {};
        const suburb = address.suburb || address.neighbourhood || address.road || address.village || "";
        const city = address.city || address.town || address.county || address.state || "";
        const placeStr = [suburb, city].filter(Boolean).join(", ") || data.display_name?.split(",").slice(0, 3).join(",");
        setReportLocation(placeStr || `${lat.toFixed(4)}, ${lng.toFixed(4)}`);
      } else {
        setReportLocation(`${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`);
      }
    } catch {
      setReportLocation(`${lat.toFixed(4)}° N, ${lng.toFixed(4)}° E`);
    }
  };

  // Handle Media File Selection
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const isImage = file.type.startsWith("image/");
    const isVideo = file.type.startsWith("video/");

    if (!isImage && !isVideo) {
      setReportError("Only image and video files are supported.");
      return;
    }

    if (file.size > 50 * 1024 * 1024) {
      setReportError("File is too large. Maximum allowed size is 50MB.");
      return;
    }

    setReportError("");
    setMediaFile(file);
    setMediaType(isImage ? "image" : "video");
    const objectUrl = URL.createObjectURL(file);
    setMediaPreviewUrl(objectUrl);
  };

  const clearSelectedMedia = () => {
    if (mediaPreviewUrl) {
      URL.revokeObjectURL(mediaPreviewUrl);
    }
    setMediaFile(null);
    setMediaPreviewUrl(null);
    setMediaType(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const authenticate = async () => {
    setAuthLoading(true);
    setAuthError("");
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    if (!authEmail.trim()) {
      setAuthError("Email is required.");
      setAuthLoading(false);
      return;
    }
    if (authMode === "register" && !authName.trim()) {
      setAuthError("Name is required.");
      setAuthLoading(false);
      return;
    }
    if (authPassword.length < 8) {
      setAuthError("Password must be at least 8 characters.");
      setAuthLoading(false);
      return;
    }
    const endpoint = authMode === "login" ? "/auth/login" : "/auth/register";
    const body =
      authMode === "login"
        ? { email: authEmail, password: authPassword }
        : { name: authName, email: authEmail, password: authPassword, role: authRole };

    try {
      const response = await fetch(`${apiUrl}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        const validationMessage = Array.isArray(payload.errors)
          ? payload.errors.map((item: { loc?: string[]; msg?: string }) => `${item.loc?.at(-1) || "field"}: ${item.msg || "invalid value"}`).join(" ")
          : "";
        throw new Error(validationMessage || payload.detail || "Authentication failed.");
      }
      localStorage.setItem("solvebridge_token", payload.access_token);
      setCurrentUser(payload.user);
      setShowAuthModal(false);
      setAuthPassword("");
      showNotice(`Signed in as ${payload.user.profile?.display_name || payload.user.email}.`);
      void loadMyReports();
      void loadAllProblems();
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Authentication failed.");
    } finally {
      setAuthLoading(false);
    }
  };

  const signOut = async () => {
    const token = localStorage.getItem("solvebridge_token");
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    if (token) {
      await fetch(`${apiUrl}/auth/logout`, { method: "POST", headers: { Authorization: `Bearer ${token}` } }).catch(() => undefined);
    }
    localStorage.removeItem("solvebridge_token");
    setCurrentUser(null);
    setMyReports([]);
    setAllProblems([]);
    setSelected(null);
    setActiveNav("Overview");
    setAuthMode("login");
    setAuthError("");
    setShowAuthModal(true);
  };

  const loadAllProblems = async () => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    try {
      const response = await fetch(`${apiUrl}/problems?page_size=100`);
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "Could not load problems.");
      const items: Problem[] = Array.isArray(payload.items)
        ? payload.items.map((item: any) => problemFromApi(item, universityLocation.lat, universityLocation.lng))
        : [];
      setAllProblems(items);
    } catch {
      // Ignored
    }
  };

  // Loads ONLY the reports created by this authenticated student/citizen!
  const loadMyReports = async () => {
    const token = localStorage.getItem("solvebridge_token");
    if (!token) {
      setMyReports([]);
      setSelected(null);
      setProblemsLoading(false);
      return;
    }
    setMyReportsLoading(true);
    setMyReportsError("");
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    try {
      const response = await fetch(`${apiUrl}/problems/me`, { headers: { Authorization: `Bearer ${token}` } });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "Could not load your reports.");
      const reports: Problem[] = Array.isArray(payload.items)
        ? payload.items.map((item: any) => problemFromApi(item, universityLocation.lat, universityLocation.lng))
        : [];
      setMyReports(reports);
      setSelected((curr) => {
        if (reports.length === 0) return null;
        if (curr && reports.some((r) => r.id === curr.id)) return curr;
        return reports[0];
      });
      setMyReportsLoading(false);
      setProblemsLoading(false);

      // Fetch matches asynchronously in background without blocking the UI
      void Promise.all(
        reports.slice(0, 5).map(async (report) => {
          const matchesResponse = await fetch(`${apiUrl}/problems/${encodeURIComponent(report.id)}/matches`);
          const matchesPayload = await matchesResponse.json().catch(() => ({}));
          return [report.id, matchesResponse.ok && Array.isArray(matchesPayload.matches) ? matchesPayload.matches : []] as const;
        })
      ).then((entries) => {
        setMyReportMatches(Object.fromEntries(entries));
      });
    } catch (error) {
      setMyReportsError(error instanceof Error ? error.message : "Could not load your reports.");
    } finally {
      setMyReportsLoading(false);
      setProblemsLoading(false);
    }
  };

  const loadCollaborations = async () => {
    const token = localStorage.getItem("solvebridge_token");
    if (!token) return;
    setCollaborationLoading(true);
    setCollaborationError("");
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    try {
      const response = await fetch(`${apiUrl}/collaborations`, { headers: { Authorization: `Bearer ${token}` } });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(payload.detail || "Could not load collaboration requests.");
      setCollaborationRequests(payload);
    } catch (error) {
      setCollaborationError(error instanceof Error ? error.message : "Could not load collaboration requests.");
    } finally {
      setCollaborationLoading(false);
    }
  };

  const supportProblem = async (problemId: string) => {
    const token = localStorage.getItem("solvebridge_token");
    if (!token) {
      showNotice("Sign in to support or confirm this problem.");
      return;
    }
    if (supportingProblem[problemId]) return;
    setSupportingProblem((prev) => ({ ...prev, [problemId]: true }));
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

    try {
      const response = await fetch(`${apiUrl}/problems/${encodeURIComponent(problemId)}/support`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 409) {
          setSupportedMap((prev) => ({ ...prev, [problemId]: true }));
          showNotice("You have already confirmed and supported this report.");
          return;
        }
        throw new Error(data.detail || "Could not support problem.");
      }

      setSupportedMap((prev) => ({ ...prev, [problemId]: true }));
      const updatedCount = data.support_count;
      setMyReports((current) => current.map((p) => (p.id === problemId ? { ...p, reports: updatedCount } : p)));
      setAllProblems((current) => current.map((p) => (p.id === problemId ? { ...p, reports: updatedCount } : p)));
      setSelected((current) => (current?.id === problemId ? { ...current, reports: updatedCount } : current));
      showNotice(`Report confirmed! Total reports: ${updatedCount}`);
    } catch (err) {
      showNotice(err instanceof Error ? err.message : "Error supporting problem");
    } finally {
      setSupportingProblem((prev) => ({ ...prev, [problemId]: false }));
    }
  };

  const sendCollaboration = async (problemId: string, match: Match) => {
    const token = localStorage.getItem("solvebridge_token");
    if (!token) {
      showNotice("Sign in before sending a collaboration request.");
      return;
    }
    if (collaborationSending[match.candidate_id]) return;
    setCollaborationSending((current) => ({ ...current, [match.candidate_id]: true }));
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    try {
      const response = await fetch(`${apiUrl}/collaborations`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({
          problem_id: problemId,
          recipient_id: match.candidate_id,
          message: "We would like to collaborate on this problem report.",
        }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 409) {
          setActiveNav("My collaborations");
          void loadCollaborations();
          throw new Error("A pending request already exists in your workspace.");
        }
        throw new Error(payload.detail || "Could not send collaboration request.");
      }
      setCollaborationRequests((current) => [payload, ...current]);
      showNotice("Collaboration request sent successfully!");
    } catch (error) {
      showNotice(error instanceof Error ? error.message : "Could not send request.");
    } finally {
      setCollaborationSending((current) => ({ ...current, [match.candidate_id]: false }));
    }
  };

  const submitReport = async () => {
    if (reportSubmitting) return;
    const description = reportDescription.trim();
    const locationText = reportLocation.trim();
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    const token = typeof window !== "undefined" ? localStorage.getItem("solvebridge_token") : null;

    if (!token) {
      setReportError("Please sign in before reporting a problem.");
      return;
    }
    if (description.length < 10) {
      setReportError("Please provide at least 10 characters describing the problem.");
      return;
    }

    setReportSubmitting(true);
    setReportError("");
    setNotice("");

    try {
      let uploadedMediaUrl: string | null = null;
      let uploadedMediaType: "image" | "video" | null = null;

      // 1. If media file attached, upload first
      if (mediaFile) {
        const formData = new FormData();
        formData.append("file", mediaFile);
        const uploadRes = await fetch(`${apiUrl}/upload`, {
          method: "POST",
          body: formData,
        });
        const uploadData = await uploadRes.json().catch(() => ({}));
        if (!uploadRes.ok) {
          throw new Error(uploadData.detail || "Media upload failed.");
        }
        uploadedMediaUrl = uploadData.url;
        uploadedMediaType = uploadData.media_type;
      }

      // 2. Submit problem report
      const response = await fetch(`${apiUrl}/problems`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          title: description.slice(0, 80) || "Community problem report",
          description,
          category: "community",
          location_text: locationText || "Location pending",
          latitude: reportLatitude,
          longitude: reportLongitude,
          metadata: {
            source: "frontend",
            media_url: uploadedMediaUrl,
            media_type: uploadedMediaType,
          },
        }),
      });

      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload.detail || "Problem submission failed.");
      }

      const created = problemFromApi(payload, universityLocation.lat, universityLocation.lng);

      // Increment student's reported events!
      setMyReports((current) => [created, ...current]);
      setAllProblems((current) => [created, ...current]);
      setSelected(created);
      setSubmitted(true);
      setShowReport(false);
      setReportDescription("");
      setReportLocation("");
      setReportLatitude(null);
      setReportLongitude(null);
      setShowMapPicker(false);
      clearSelectedMedia();
      showNotice("Report submitted successfully! Added to your reported events.");
    } catch (error) {
      const message = error instanceof Error ? error.message : "Problem submission failed.";
      setReportError(message);
      setSubmitted(false);
    } finally {
      setReportSubmitting(false);
    }
  };

  const sendChat = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = chatInput.trim();
    if (!message) return;
    setChatInput("");
    setChatMessages((current) => [...current, { role: "user", text: message }]);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      });
      const result = await response.json();
      setChatMessages((current) => [...current, { role: "assistant", text: result.reply || "I could not answer that yet." }]);
    } catch {
      setChatMessages((current) => [
        ...current,
        { role: "assistant", text: "I’m having trouble reaching the assistant. You can still submit reports with evidence and location." },
      ]);
    }
  };

  // Auth bootstrap
  useEffect(() => {
    const token = localStorage.getItem("solvebridge_token");
    if (!token) {
      setAuthChecked(true);
      setProblemsLoading(false);
      return;
    }
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    fetch(`${apiUrl}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        if (!response.ok) throw new Error("Session expired.");
        return response.json();
      })
      .then((user) => {
        setCurrentUser(user);
        void loadMyReports();
        void loadAllProblems();
      })
      .catch(() => {
        localStorage.removeItem("solvebridge_token");
        setCurrentUser(null);
        setProblemsLoading(false);
      })
      .finally(() => {
        setAuthChecked(true);
      });
  }, []);

  // Fetch matches for selected problem
  useEffect(() => {
    if (!selected) {
      setMatches([]);
      setMatchesLoading(false);
      return;
    }
    let cancelled = false;
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
    setMatchesLoading(true);
    fetch(`${apiUrl}/problems/${encodeURIComponent(selected.id)}/matches`)
      .then(async (response) => {
        const payload = await response.json().catch(() => ({}));
        if (!response.ok) throw new Error(payload.detail || "Could not load collaborators.");
        return payload;
      })
      .then((result) => {
        if (!cancelled) setMatches((result.matches || []).slice(0, 3));
      })
      .catch(() => {
        if (!cancelled) setMatches([]);
      })
      .finally(() => {
        if (!cancelled) setMatchesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selected?.id]);

  useEffect(() => {
    if (activeNav === "My reports") void loadMyReports();
    if (activeNav === "My collaborations") void loadCollaborations();
  }, [activeNav]);

  // STUDENT / CITIZEN SEES ONLY THEIR REPORTED EVENTS!
  const studentReports = myReports.filter((problem) =>
    `${problem.title} ${problem.place} ${problem.tags.join(" ")} ${problem.description}`
      .toLowerCase()
      .includes(searchQuery.toLowerCase())
  );

  // University problems (all nearby community issues)
  const universityProblems = allProblems.filter((problem) => {
    if (universityRadiusKm < 999 && problem.distance_km != null && problem.distance_km > universityRadiusKm) {
      return false;
    }
    if (universityDisciplineFilter !== "all") {
      const tags = (problem.analysis?.tags || problem.tags).map((t) => t.toLowerCase());
      const skills = (problem.analysis?.required_skills || []).map((s) => s.toLowerCase());
      const allTerms = [...tags, ...skills].join(" ");
      if (universityDisciplineFilter === "civil" && !allTerms.includes("civil") && !allTerms.includes("road") && !allTerms.includes("infrastructure")) return false;
      if (universityDisciplineFilter === "water" && !allTerms.includes("water") && !allTerms.includes("drainage") && !allTerms.includes("environmental")) return false;
      if (universityDisciplineFilter === "tech" && !allTerms.includes("iot") && !allTerms.includes("sensor") && !allTerms.includes("tech")) return false;
      if (universityDisciplineFilter === "health" && !allTerms.includes("health") && !allTerms.includes("sanitation")) return false;
    }
    return true;
  });

  if (!authChecked) {
    return <EmptyState message="Loading..." />;
  }

  if (!currentUser) {
    return (
      <AuthScreen
        mode={authMode}
        email={authEmail}
        password={authPassword}
        name={authName}
        role={authRole}
        error={authError}
        loading={authLoading}
        passwordVisible={passwordVisible}
        setMode={setAuthMode}
        setEmail={setAuthEmail}
        setPassword={setAuthPassword}
        setName={setAuthName}
        setRole={setAuthRole}
        setPasswordVisible={setPasswordVisible}
        onSubmit={() => void authenticate()}
      />
    );
  }

  // Fallback for selected
  const activeSelected = isUniversity
    ? selected ?? universityProblems[0] ?? null
    : selected ?? studentReports[0] ?? null;

  return (
    <main className="app-shell">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <Waypoints size={19} />
          </div>
          <span>jansethu</span>
        </div>

        <button className="profile-chip" onClick={() => void signOut()} title="Click to sign out">
          <div className="avatar">
            {(currentUser.profile?.display_name || currentUser.email).slice(0, 2).toUpperCase()}
          </div>
          <div>
            <strong>{currentUser.profile?.display_name || currentUser.email}</strong>
            <small style={{ textTransform: "capitalize" }}>
              Role: {currentUser.role}
            </small>
          </div>
          <LogOut size={16} />
        </button>

        {/* Role identification badge (No manual toggle: strictly based on account role!) */}
        <div style={{ margin: "0 4px 18px", padding: "8px 12px", background: "#e8f3ed", borderRadius: 8, border: "1px solid #cbe3d6" }}>
          <small style={{ display: "block", fontSize: 10, color: "var(--teal)", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Active Interface
          </small>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 3 }}>
            {isUniversity ? <GraduationCap size={15} color="var(--teal)" /> : <UsersRound size={15} color="var(--teal)" />}
            <strong style={{ fontSize: 12, color: "var(--ink)", textTransform: "capitalize" }}>
              {isUniversity ? "University Portal" : `${currentUser.role} Interface`}
            </strong>
          </div>
        </div>

        <p className="eyebrow">Workspace</p>
        <nav>
          {["Overview", "Report a problem", "My reports", "My collaborations"].map((item, index) => (
            <button
              key={item}
              className={activeNav === item ? "nav-item active" : "nav-item"}
              onClick={() => {
                setActiveNav(item);
                if (item === "Report a problem") setShowReport(true);
                if (item === "My collaborations") void loadCollaborations();
                if (item === "My reports") void loadMyReports();
              }}
            >
              <span className="nav-icon">
                {[
                  <Activity key="a" size={18} />,
                  <Plus key="b" size={18} />,
                  <FileText key="c" size={18} />,
                  <Users key="d" size={18} />,
                ][index]}
              </span>
              {item}
              {item === "My reports" && (
                <span className="nav-count" style={{ background: "#d0e3db", color: "#176b61" }}>
                  {myReports.length}
                </span>
              )}
              {item === "My collaborations" && collaborationRequests.some((r) => r.status === "pending") && (
                <span className="nav-count">{collaborationRequests.filter((r) => r.status === "pending").length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="help" onClick={() => setChatOpen(true)}>
            <CircleHelp size={18} />
            <span>
              <strong>Need a hand?</strong>
              <small>Learn how jansethu works</small>
            </span>
          </button>
          <button className="nav-item" onClick={() => showNotice("Your data is secure and visible only to verified collaborators.")}>
            <span className="nav-icon">
              <ShieldCheck size={18} />
            </span>
            Trust & Safety
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <section className="content">
        <header className="topbar">
          <div className="mobile-brand">
            <div className="brand-mark">
              <Waypoints size={17} />
            </div>
            jansethu
          </div>
          <div className="search">
            <Search size={17} />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search your reported events..."
              aria-label="Search"
            />
          </div>
          <div className="top-actions">
            <button className="icon-button" onClick={() => showNotice("All notifications caught up.")} aria-label="Notifications">
              <Bell size={19} />
              <span className="notification-dot" />
            </button>
            <button className="avatar small" onClick={() => void signOut()} aria-label="Sign out">
              <LogOut size={15} />
            </button>
            <button className="icon-button menu-button" onClick={() => setChatOpen(true)} aria-label="Help">
              <Menu size={20} />
            </button>
          </div>
        </header>

        {/* 1. STUDENT & CITIZEN INTERFACE (SHOWS ONLY THEIR REPORTED EVENTS!) */}
        {!isUniversity && (
          <div className="page-wrap" style={{ display: activeNav !== "Overview" ? "none" : undefined }}>
            <div className="welcome-row">
              <div>
                <p className="kicker">{currentUser.role.toUpperCase()} PORTAL</p>
                <h1>Hi, {displayName}.</h1>
                <p className="subhead">Manage and track only the civic events and problems you have reported.</p>
              </div>
              <button className="primary-button" onClick={() => setShowReport(true)}>
                <Plus size={18} />
                Report a problem
              </button>
            </div>

            {submitted && (
              <div className="toast">
                <Sparkles size={17} />
                <span>
                  <strong>Report registered!</strong> Your problem has been added to your reported events list.
                </span>
                <button onClick={() => setSubmitted(false)}>
                  <X size={16} />
                </button>
              </div>
            )}
            {notice && (
              <div className="toast">
                <ShieldCheck size={17} />
                <span>{notice}</span>
                <button onClick={() => setNotice("")}>
                  <X size={16} />
                </button>
              </div>
            )}

            {/* Stats: Starts at 0 for new user, increments on report creation */}
            <div className="stats-grid">
              <Stat
                icon={<FileText size={18} />}
                label="Your reported events"
                value={String(myReports.length)}
                detail={myReports.length === 0 ? "0 submitted so far" : `${myReports.length} reported by you`}
                accent="blue"
              />
              <Stat
                icon={<ThumbsUp size={18} />}
                label="Total community support"
                value={String(myReports.reduce((acc, curr) => acc + (curr.reports || 1), 0))}
                detail="Citizens confirming your reports"
                accent="orange"
              />
              <Stat
                icon={<GraduationCap size={18} />}
                label="University matches"
                value={String(Object.values(myReportMatches).reduce((acc, m) => acc + m.length, 0))}
                detail="Academic & lab partners"
                accent="green"
              />
              <Stat
                icon={<Activity size={18} />}
                label="Status"
                value={myReports.length > 0 ? "Active" : "Ready"}
                detail={myReports.length > 0 ? "Issues under AI analysis" : "Waiting for your first report"}
                accent="purple"
              />
            </div>

            {/* If 0 reports, show helpful empty state */}
            {studentReports.length === 0 ? (
              <div
                style={{
                  background: "white",
                  border: "1px solid var(--line)",
                  borderRadius: 12,
                  padding: "60px 20px",
                  textAlign: "center",
                  marginTop: 10,
                }}
              >
                <div
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: "50%",
                    background: "#e8f3ee",
                    color: "var(--teal)",
                    display: "grid",
                    placeItems: "center",
                    margin: "0 auto 16px",
                  }}
                >
                  <FileText size={26} />
                </div>
                <h2 style={{ fontFamily: "'Space Grotesk', sans-serif", fontSize: 22, margin: "0 0 8px" }}>
                  No reported events yet
                </h2>
                <p style={{ color: "var(--muted)", fontSize: 13, maxWidth: 440, margin: "0 auto 20px" }}>
                  You haven't reported any problems yet. Click the button below to report an issue, choose your location (GPS or select on map), and attach photo/video evidence.
                </p>
                <button className="primary-button" onClick={() => setShowReport(true)}>
                  <Plus size={18} />
                  Report your first problem
                </button>
              </div>
            ) : (
              <div className="main-grid">
                {/* Map of ONLY user's reported events */}
                <section className="map-panel panel">
                  <div className="panel-heading">
                    <div>
                      <p className="kicker">YOUR REPORTED LOCATIONS</p>
                      <h2>My reported events map ({studentReports.length})</h2>
                    </div>
                  </div>
                  <div className="map-canvas">
                    <LeafletMap
                      problems={studentReports}
                      onSelect={(p) => setSelected(p)}
                      emptyText="None of your reported events have valid map coordinates."
                    />
                  </div>
                </section>

                {/* Detail Panel of user's selected report */}
                {activeSelected && (
                  <section className="detail-panel panel">
                    <div className="detail-top">
                      <span className={`status-pill ${activeSelected.severity === "High" ? "danger" : "calm"}`}>
                        {activeSelected.severity === "High" ? "●" : "○"} {activeSelected.status}
                      </span>
                    </div>

                    <h2>{activeSelected.title}</h2>
                    <p className="location">
                      <MapPin size={15} />
                      {activeSelected.place}
                    </p>

                    {/* Media view (Image or Video) */}
                    {activeSelected.media_url && (
                      <div style={{ margin: "14px 0", borderRadius: 8, overflow: "hidden", border: "1px solid var(--line)" }}>
                        {activeSelected.media_type === "video" || activeSelected.media_url.endsWith(".mp4") ? (
                          <video
                            src={getFullMediaUrl(activeSelected.media_url)}
                            controls
                            style={{ width: "100%", maxHeight: 220, display: "block", background: "#000" }}
                          />
                        ) : (
                          <img
                            src={getFullMediaUrl(activeSelected.media_url)}
                            alt={activeSelected.title}
                            style={{ width: "100%", maxHeight: 220, objectFit: "cover", display: "block" }}
                          />
                        )}
                      </div>
                    )}

                    <p style={{ fontSize: 12, color: "var(--ink)", lineHeight: 1.5, margin: "10px 0" }}>
                      {activeSelected.description}
                    </p>

                    {/* Support / Confirm (+1 count) */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        padding: "10px 12px",
                        background: "#f2f8f5",
                        borderRadius: 8,
                        margin: "14px 0",
                      }}
                    >
                      <div className="support-line" style={{ margin: 0 }}>
                        <div className="mini-avatars">
                          <span>RK</span>
                          <span>MT</span>
                          <span>+{Math.max(activeSelected.reports - 2, 0)}</span>
                        </div>
                        <span>
                          <strong>{activeSelected.reports} citizens</strong> reported / support this
                        </span>
                      </div>

                      <button
                        style={{
                          border: "none",
                          borderRadius: 6,
                          background: supportedMap[activeSelected.id] ? "#287e63" : "var(--teal)",
                          color: "white",
                          padding: "6px 12px",
                          fontSize: 11,
                          fontWeight: 700,
                          display: "flex",
                          alignItems: "center",
                          gap: 5,
                          cursor: "pointer",
                        }}
                        disabled={supportingProblem[activeSelected.id]}
                        onClick={() => void supportProblem(activeSelected.id)}
                      >
                        {supportedMap[activeSelected.id] ? (
                          <>
                            <Check size={14} /> Supported
                          </>
                        ) : (
                          <>
                            <ThumbsUp size={13} /> +1 Support Report
                          </>
                        )}
                      </button>
                    </div>

                    <div className="detail-divider" />
                    <p className="kicker">AI-IDENTIFIED NEEDS</p>
                    <div className="tag-list">
                      {(activeSelected.analysis?.tags || activeSelected.tags).map((tag) => (
                        <span className="tag" key={tag}>
                          {tag}
                        </span>
                      ))}
                    </div>

                    <p className="kicker match-kicker">UNIVERSITY & EXPERT MATCHES</p>
                    {matchesLoading ? (
                      <div className="match-card">
                        <div className="match-icon">
                          <Sparkles size={17} />
                        </div>
                        <div>
                          <strong>Finding matching university labs...</strong>
                        </div>
                      </div>
                    ) : matches.length === 0 ? (
                      <div className="match-card">
                        <div className="match-icon">
                          <Users size={17} />
                        </div>
                        <div>
                          <strong>No matched university profiles yet</strong>
                          <p>AI will pair this problem with university capstone projects.</p>
                        </div>
                      </div>
                    ) : (
                      <div className="match-list">
                        {matches.map((match) => (
                          <div className="match-result" key={match.candidate_id}>
                            <span className="match-score">{match.score}%</span>
                            <span className="match-copy">
                              <strong>{match.name}</strong>
                              <small>
                                {match.role} · {match.organization}
                              </small>
                              <em>{match.explanation}</em>
                            </span>
                            <button
                              className="text-button"
                              disabled={collaborationSending[match.candidate_id]}
                              onClick={() => void sendCollaboration(activeSelected.id, match)}
                            >
                              {collaborationSending[match.candidate_id] ? "Sending..." : "Collaborate"}
                            </button>
                            <ChevronRight size={15} />
                          </div>
                        ))}
                      </div>
                    )}
                  </section>
                )}
              </div>
            )}
          </div>
        )}

        {/* 2. UNIVERSITY INTERFACE (ONLY FOR UNIVERSITY / RESEARCHER ACCOUNTS) */}
        {isUniversity && (
          <div className="page-wrap" style={{ display: activeNav !== "Overview" ? "none" : undefined }}>
            <div className="welcome-row" style={{ alignItems: "flex-start" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                  <span
                    style={{
                      background: "#e1f0e9",
                      color: "var(--teal)",
                      padding: "4px 9px",
                      borderRadius: 6,
                      fontSize: 11,
                      fontWeight: 700,
                      display: "flex",
                      alignItems: "center",
                      gap: 4,
                    }}
                  >
                    <GraduationCap size={14} /> University Innovation & Research Portal
                  </span>
                </div>
                <h1>Nearby Civic Problems Feed</h1>
                <p className="subhead">
                  Discover local problems in your area, adopt real issues for student capstones, and offer applied university lab capabilities.
                </p>
              </div>

              {/* Campus Location */}
              <div
                style={{
                  background: "white",
                  border: "1px solid var(--line)",
                  borderRadius: 10,
                  padding: "12px 16px",
                  display: "flex",
                  flexDirection: "column",
                  gap: 8,
                  minWidth: 280,
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 700 }}>CAMPUS LOCATION</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 13, fontWeight: 600 }}>
                  <MapPin size={16} color="var(--teal)" />
                  <span>{universityLocation.name}</span>
                </div>
                <small style={{ color: "var(--muted)", fontSize: 10 }}>
                  Base Coordinates: {universityLocation.lat.toFixed(4)}, {universityLocation.lng.toFixed(4)}
                </small>
              </div>
            </div>

            {notice && (
              <div className="toast">
                <ShieldCheck size={17} />
                <span>{notice}</span>
                <button onClick={() => setNotice("")}>
                  <X size={16} />
                </button>
              </div>
            )}

            {/* University Radius & Discipline Filters */}
            <div
              style={{
                background: "white",
                border: "1px solid var(--line)",
                borderRadius: 10,
                padding: "14px 18px",
                marginBottom: 22,
                display: "flex",
                flexWrap: "wrap",
                gap: 16,
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>RADIUS:</span>
                {[
                  { label: "Within 5 km", val: 5 },
                  { label: "Within 15 km", val: 15 },
                  { label: "Within 50 km", val: 50 },
                  { label: "All Regions", val: 999 },
                ].map((r) => (
                  <button
                    key={r.label}
                    onClick={() => setUniversityRadiusKm(r.val)}
                    style={{
                      border: "none",
                      borderRadius: 6,
                      padding: "6px 10px",
                      fontSize: 11,
                      fontWeight: 700,
                      background: universityRadiusKm === r.val ? "var(--teal)" : "#edf4f0",
                      color: universityRadiusKm === r.val ? "white" : "var(--ink)",
                      cursor: "pointer",
                    }}
                  >
                    {r.label}
                  </button>
                ))}
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: "var(--muted)" }}>FIELD:</span>
                {[
                  { label: "All Disciplines", key: "all" },
                  { label: "Civil / Roads", key: "civil" },
                  { label: "Water / Eco", key: "water" },
                  { label: "IoT / Sensors", key: "tech" },
                  { label: "Health / Waste", key: "health" },
                ].map((d) => (
                  <button
                    key={d.key}
                    onClick={() => setUniversityDisciplineFilter(d.key)}
                    style={{
                      border: "none",
                      borderRadius: 6,
                      padding: "6px 10px",
                      fontSize: 11,
                      fontWeight: 700,
                      background: universityDisciplineFilter === d.key ? "#dbece3" : "transparent",
                      color: "var(--teal)",
                      cursor: "pointer",
                    }}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>

            {/* University Stats */}
            <div className="stats-grid">
              <Stat
                icon={<MapPin size={18} />}
                label="Problems nearby"
                value={String(universityProblems.length)}
                detail={universityRadiusKm < 999 ? `Within ${universityRadiusKm}km of campus` : "Across all regions"}
                accent="blue"
              />
              <Stat
                icon={<GraduationCap size={18} />}
                label="Student capstones"
                value={String(universityProblems.filter((p) => p.severity === "High" || p.severity === "Medium").length)}
                detail="Ready for academic teams"
                accent="green"
              />
              <Stat
                icon={<Sparkles size={18} />}
                label="AI needed skills"
                value="18+"
                detail="Engineering, IoT & Environment"
                accent="purple"
              />
              <Stat
                icon={<Building2 size={18} />}
                label="Active proposals"
                value={String(collaborationRequests.length)}
                detail="Sent by your institution"
                accent="orange"
              />
            </div>

            {/* University Main Grid */}
            <div className="main-grid">
              <section className="panel" style={{ padding: 20 }}>
                <div className="panel-heading">
                  <div>
                    <p className="kicker">CAMPUS PROXIMITY FEED</p>
                    <h2>Nearby problems ({universityProblems.length})</h2>
                  </div>
                  <small style={{ color: "var(--muted)" }}>Sorted by closest distance</small>
                </div>

                {universityProblems.length === 0 ? (
                  <div style={{ textAlign: "center", padding: "40px 20px", color: "var(--muted)" }}>
                    <Compass size={32} style={{ margin: "0 auto 10px", color: "var(--teal)" }} />
                    <strong>No problems match your current distance or discipline filter.</strong>
                    <p style={{ fontSize: 12 }}>Try expanding the radius to 50km or All Regions.</p>
                  </div>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
                    {universityProblems.map((problem) => (
                      <div
                        key={problem.id}
                        onClick={() => setSelected(problem)}
                        style={{
                          border: activeSelected?.id === problem.id ? "2px solid var(--teal)" : "1px solid var(--line)",
                          background: activeSelected?.id === problem.id ? "#f6fbf8" : "white",
                          borderRadius: 10,
                          padding: 16,
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 8 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span className={`status-pill ${problem.severity === "High" ? "danger" : "calm"}`}>
                              {problem.severity}
                            </span>
                            {problem.distance_km != null && (
                              <span
                                style={{
                                  background: "#e8f3ee",
                                  color: "var(--teal)",
                                  fontSize: 11,
                                  fontWeight: 700,
                                  padding: "4px 8px",
                                  borderRadius: 5,
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: 4,
                                }}
                              >
                                📍 {problem.distance_km} km away
                              </span>
                            )}
                          </div>
                          <span style={{ fontSize: 11, color: "var(--muted)", fontWeight: 600 }}>
                            {problem.reports} citizen reports
                          </span>
                        </div>

                        <h3 style={{ fontSize: 15, margin: "0 0 6px", fontFamily: "'Space Grotesk', sans-serif" }}>
                          {problem.title}
                        </h3>
                        <p style={{ fontSize: 12, color: "var(--muted)", margin: "0 0 10px", display: "flex", alignItems: "center", gap: 4 }}>
                          <MapPin size={13} /> {problem.place}
                        </p>

                        {problem.media_url && (
                          <div style={{ margin: "8px 0", maxHeight: 110, overflow: "hidden", borderRadius: 6, background: "#000" }}>
                            {problem.media_type === "video" || problem.media_url.endsWith(".mp4") ? (
                              <video src={getFullMediaUrl(problem.media_url)} style={{ width: "100%", maxHeight: 110, objectFit: "cover" }} />
                            ) : (
                              <img src={getFullMediaUrl(problem.media_url)} alt={problem.title} style={{ width: "100%", maxHeight: 110, objectFit: "cover" }} />
                            )}
                          </div>
                        )}

                        <p style={{ fontSize: 12, color: "var(--ink)", margin: "0 0 12px", lineHeight: 1.4 }}>
                          {(problem.description || "").slice(0, 160)}...
                        </p>

                        <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 12 }}>
                          {(problem.analysis?.required_skills || problem.tags).slice(0, 4).map((s) => (
                            <span key={s} style={{ background: "#eef5f1", color: "#246457", fontSize: 10, padding: "3px 7px", borderRadius: 4 }}>
                              {s}
                            </span>
                          ))}
                        </div>

                        <div style={{ display: "flex", gap: 8, borderTop: "1px solid #edf3ef", paddingTop: 10 }}>
                          <button
                            style={{
                              background: "var(--teal)",
                              color: "white",
                              border: "none",
                              padding: "7px 12px",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 700,
                              cursor: "pointer",
                              display: "flex",
                              alignItems: "center",
                              gap: 5,
                            }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelected(problem);
                              showNotice(`Adopted "${problem.title}" for university capstone project initiative!`);
                            }}
                          >
                            <GraduationCap size={14} /> Adopt for Capstone
                          </button>
                          <button
                            style={{
                              background: "white",
                              border: "1px solid var(--line)",
                              color: "var(--teal)",
                              padding: "7px 12px",
                              borderRadius: 6,
                              fontSize: 11,
                              fontWeight: 700,
                              cursor: "pointer",
                            }}
                            onClick={(e) => {
                              e.stopPropagation();
                              setSelected(problem);
                            }}
                          >
                            Inspect Details
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              {/* University Detail Inspection */}
              {activeSelected && (
                <section className="detail-panel panel">
                  <div className="panel-heading">
                    <div>
                      <p className="kicker">CAMPUS MAP & PROBLEM INSPECTION</p>
                      <h2>Problem inspection</h2>
                    </div>
                  </div>

                  <div style={{ height: 230, borderRadius: 8, overflow: "hidden", marginBottom: 16, position: "relative" }}>
                    <LeafletMap
                      problems={universityProblems}
                      onSelect={(p) => setSelected(p)}
                      centerCoords={{ lat: universityLocation.lat, lng: universityLocation.lng }}
                    />
                  </div>

                  <div className="detail-top">
                    <span className={`status-pill ${activeSelected.severity === "High" ? "danger" : "calm"}`}>
                      {activeSelected.severity} Severity
                    </span>
                    {activeSelected.distance_km != null && (
                      <span style={{ fontSize: 12, fontWeight: 700, color: "var(--teal)" }}>
                        📍 {activeSelected.distance_km} km from campus
                      </span>
                    )}
                  </div>

                  <h2>{activeSelected.title}</h2>
                  <p className="location">
                    <MapPin size={15} />
                    {activeSelected.place}
                  </p>

                  {activeSelected.media_url && (
                    <div style={{ margin: "14px 0", borderRadius: 8, overflow: "hidden", border: "1px solid var(--line)" }}>
                      {activeSelected.media_type === "video" || activeSelected.media_url.endsWith(".mp4") ? (
                        <video src={getFullMediaUrl(activeSelected.media_url)} controls style={{ width: "100%", maxHeight: 240, display: "block", background: "#000" }} />
                      ) : (
                        <img src={getFullMediaUrl(activeSelected.media_url)} alt={activeSelected.title} style={{ width: "100%", maxHeight: 240, objectFit: "cover", display: "block" }} />
                      )}
                    </div>
                  )}

                  <p style={{ fontSize: 12, color: "var(--ink)", lineHeight: 1.5, margin: "10px 0" }}>
                    {activeSelected.description}
                  </p>

                  <div className="detail-divider" />
                  <p className="kicker">ACADEMIC & RESEARCH DISCIPLINES</p>
                  <div className="tag-list">
                    {(activeSelected.analysis?.required_skills || activeSelected.tags).map((tag) => (
                      <span className="tag" key={tag}>
                        {tag}
                      </span>
                    ))}
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 16 }}>
                    <button
                      className="primary-button"
                      onClick={() => {
                        showNotice(`Proposal initiated: University research team dispatched for "${activeSelected.title}".`);
                      }}
                    >
                      <GraduationCap size={16} /> Submit University Capstone Proposal
                    </button>
                    <button className="secondary-button" onClick={() => void supportProblem(activeSelected.id)}>
                      <ThumbsUp size={15} /> Confirm Problem Severity ({activeSelected.reports} Reports)
                    </button>
                  </div>
                </section>
              )}
            </div>
          </div>
        )}

        {/* MY REPORTS TAB */}
        {activeNav === "My reports" && (
          <section className="panel workspace-overlay" style={{ position: "fixed", zIndex: 8, top: 76, left: 260, right: 24, bottom: 24, overflow: "auto" }}>
            <div className="panel-heading">
              <div>
                <p className="kicker">YOUR SUBMITTED REPORTS</p>
                <h2>My reports ({myReports.length})</h2>
                <p>Events and issues submitted by your authenticated account.</p>
              </div>
              <button className="icon-button" onClick={() => void loadMyReports()} aria-label="Refresh">
                <ArrowUpRight size={18} />
              </button>
            </div>

            {myReportsLoading ? (
              <div className="match-card">
                <strong>Loading your reports...</strong>
              </div>
            ) : myReportsError ? (
              <div className="match-card">
                <strong>{myReportsError}</strong>
              </div>
            ) : myReports.length === 0 ? (
              <div className="match-card" style={{ padding: 30, textAlign: "center" }}>
                <FileText size={32} color="var(--teal)" style={{ margin: "0 auto 10px" }} />
                <strong>No reports yet (0 reports)</strong>
                <p style={{ marginTop: 6 }}>Click "Report a problem" to submit your first local observation!</p>
                <button className="primary-button" style={{ marginTop: 14 }} onClick={() => setShowReport(true)}>
                  <Plus size={16} /> Report a problem
                </button>
              </div>
            ) : (
              <div className="match-list">
                {myReports.map((report) => (
                  <button
                    className="match-result activity-button"
                    key={report.id}
                    onClick={() => {
                      setSelected(report);
                      setActiveNav("Overview");
                    }}
                  >
                    <span className="match-score">{report.reports}</span>
                    <span className="match-copy">
                      <strong>{report.title}</strong>
                      <small>
                        {report.place} · {report.status}
                      </small>
                      <em>{report.tags.length ? report.tags.join(" · ") : "Civic report"}</em>
                    </span>
                    <ChevronRight size={15} />
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        {/* MY COLLABORATIONS TAB */}
        {activeNav === "My collaborations" && (
          <section
            className="panel workspace-overlay"
            style={{ position: "fixed", zIndex: 12, top: 76, left: 260, right: 24, bottom: 24, overflow: "auto", background: "var(--paper)", padding: 24 }}
          >
            <div className="panel-heading">
              <div>
                <p className="kicker">COLLABORATION WORKSPACE</p>
                <h2>My collaborations</h2>
                <p>Review and manage active university & industry partnerships.</p>
              </div>
              <button className="icon-button" onClick={() => setActiveNav("Overview")} aria-label="Close">
                <X size={18} />
              </button>
            </div>
            {collaborationLoading ? (
              <div className="match-card">
                <strong>Loading requests...</strong>
              </div>
            ) : collaborationError ? (
              <div className="match-card">
                <strong>{collaborationError}</strong>
              </div>
            ) : collaborationRequests.length === 0 ? (
              <div className="match-card">
                <strong>No collaboration requests yet</strong>
                <p>Collaboration requests from universities or partners will appear here.</p>
              </div>
            ) : (
              <div className="match-list">
                {collaborationRequests.map((request) => (
                  <div className="match-result" key={`workspace-${request.id}`}>
                    <span className="match-score">{request.status.slice(0, 1).toUpperCase()}</span>
                    <span className="match-copy">
                      <strong>Status: {request.status}</strong>
                      <small>Problem ID: {request.problem_id}</small>
                      <em>{request.message || "Collaboration request"}</em>
                    </span>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}
      </section>

      {/* REPORT A PROBLEM MODAL (with Rapido-style Current Location OR Pick on Map + Photo/Video upload) */}
      {showReport && (
        <div className="modal-backdrop" onClick={() => setShowReport(false)}>
          <div className="report-modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 640 }}>
            <div className="modal-heading">
              <div>
                <p className="kicker">EVENT & PROBLEM REPORTING</p>
                <h2>What needs attention?</h2>
                <p>Choose your location (current GPS or pick on map) and attach photo/video evidence.</p>
              </div>
              <button className="icon-button" type="button" onClick={() => setShowReport(false)}>
                <X size={19} />
              </button>
            </div>

            <div>
              <label>
                Problem description
                <textarea
                  name="description"
                  value={reportDescription}
                  onChange={(e) => setReportDescription(e.target.value)}
                  placeholder="For example: Heavy rain has accumulated in the college underpass blocking vehicles and students..."
                />
              </label>

              {/* Rapido-Style Location Selector: "Use Current Location" OR "Select on Map" */}
              <div style={{ marginBottom: 16 }}>
                <span style={{ display: "block", color: "#536760", fontSize: 11, fontWeight: 700, marginBottom: 8 }}>
                  Location of Issue
                </span>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
                  <button
                    type="button"
                    onClick={detectLocation}
                    disabled={locatingUser}
                    style={{
                      border: "1px solid var(--line)",
                      background: locatingUser ? "#eef6f2" : "#f5f9f6",
                      color: "var(--teal)",
                      padding: "10px 12px",
                      borderRadius: 8,
                      fontSize: 11,
                      fontWeight: 700,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <Navigation size={14} />
                    {locatingUser ? "Detecting GPS..." : "📍 Choose Current Location"}
                  </button>

                  <button
                    type="button"
                    onClick={() => setShowMapPicker(!showMapPicker)}
                    style={{
                      border: showMapPicker ? "2px solid var(--teal)" : "1px solid var(--line)",
                      background: showMapPicker ? "#e1f0e9" : "#f5f9f6",
                      color: "var(--teal)",
                      padding: "10px 12px",
                      borderRadius: 8,
                      fontSize: 11,
                      fontWeight: 700,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      gap: 6,
                      cursor: "pointer",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <MapPin size={14} />
                    {showMapPicker ? "Close Map Picker" : "🗺️ Select on Map"}
                  </button>
                </div>

                {/* Interactive Map Picker (Draggable Pin) */}
                {showMapPicker && (
                  <div
                    style={{
                      marginBottom: 10,
                      border: "2px solid var(--teal)",
                      borderRadius: 10,
                      padding: 10,
                      background: "#fbfdfb",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                      <small style={{ color: "var(--teal)", fontWeight: 700, fontSize: 11 }}>
                        Click anywhere or drag the pin to set the exact spot:
                      </small>
                      <button
                        type="button"
                        onClick={() => setShowMapPicker(false)}
                        style={{
                          border: "none",
                          background: "var(--teal)",
                          color: "white",
                          padding: "3px 8px",
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          cursor: "pointer",
                        }}
                      >
                        Done ✓
                      </button>
                    </div>
                    <LocationPickerMap
                      initialLat={reportLatitude}
                      initialLng={reportLongitude}
                      onLocationSelect={(lat, lng) => void handleLocationPicked(lat, lng)}
                    />
                  </div>
                )}

                <input
                  name="location"
                  value={reportLocation}
                  onChange={(e) => setReportLocation(e.target.value)}
                  placeholder="Address, neighborhood, street or landmark"
                  style={{
                    display: "block",
                    width: "100%",
                    border: "1px solid var(--line)",
                    borderRadius: 7,
                    padding: "11px 12px",
                    outline: "none",
                    fontSize: 12,
                  }}
                />

                {reportLatitude != null && reportLongitude != null && (
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 5 }}>
                    <small style={{ color: "var(--teal)", fontSize: 10, fontWeight: 700 }}>
                      ✓ Coordinates: {reportLatitude.toFixed(4)}° N, {reportLongitude.toFixed(4)}° E
                    </small>
                    <button
                      type="button"
                      onClick={() => {
                        setReportLatitude(null);
                        setReportLongitude(null);
                        setReportLocation("");
                      }}
                      style={{ border: "none", background: "none", color: "#b5473f", fontSize: 10, cursor: "pointer", padding: 0 }}
                    >
                      (Clear)
                    </button>
                  </div>
                )}
              </div>

              {/* Media Upload (Photo or Video) */}
              <div style={{ marginBottom: 18 }}>
                <span style={{ display: "block", color: "#536760", fontSize: 11, fontWeight: 700, marginBottom: 6 }}>
                  Evidence (Photo or Video)
                </span>

                <input
                  type="file"
                  ref={fileInputRef}
                  accept="image/*,video/*"
                  onChange={handleFileSelect}
                  style={{ display: "none" }}
                />

                {!mediaFile ? (
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                      border: "2px dashed #b9cec4",
                      borderRadius: 8,
                      padding: "18px 16px",
                      textAlign: "center",
                      cursor: "pointer",
                      background: "#f9fcfb",
                      transition: "all 0.15s ease",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "center", gap: 10, marginBottom: 6, color: "var(--teal)" }}>
                      <Camera size={22} />
                      <Video size={22} />
                    </div>
                    <strong style={{ fontSize: 12, color: "var(--teal)", display: "block" }}>
                      Click to upload photo or video
                    </strong>
                    <small style={{ color: "var(--muted)", fontSize: 10 }}>
                      Supports JPG, PNG, WEBP, MP4, WEBM (up to 50MB)
                    </small>
                  </div>
                ) : (
                  <div
                    style={{
                      border: "1px solid var(--line)",
                      borderRadius: 8,
                      padding: 12,
                      background: "#fbfdfb",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: "var(--teal)" }}>
                        {mediaType === "video" ? "📹 Video attached" : "📷 Photo attached"}: {mediaFile.name}
                      </span>
                      <button
                        type="button"
                        onClick={clearSelectedMedia}
                        style={{
                          border: "none",
                          background: "#feeceb",
                          color: "#c24137",
                          padding: "3px 7px",
                          borderRadius: 4,
                          fontSize: 10,
                          fontWeight: 700,
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: 3,
                        }}
                      >
                        <X size={12} /> Remove
                      </button>
                    </div>

                    {mediaPreviewUrl && (
                      <div style={{ maxHeight: 180, overflow: "hidden", borderRadius: 6, background: "#000" }}>
                        {mediaType === "video" ? (
                          <video src={mediaPreviewUrl} controls style={{ width: "100%", maxHeight: 180, display: "block" }} />
                        ) : (
                          <img src={mediaPreviewUrl} alt="Upload preview" style={{ width: "100%", maxHeight: 180, objectFit: "contain", display: "block" }} />
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <div className="privacy-note">
                <ShieldCheck size={17} />
                <span>Your report is shared with verified universities and researchers to build real solutions.</span>
              </div>

              {reportError && (
                <p role="alert" className="report-error" style={{ color: "#b5473f", fontSize: 11, marginBottom: 12 }}>
                  {reportError}
                </p>
              )}

              <button
                className="primary-button submit-button"
                type="button"
                onClick={() => void submitReport()}
                disabled={reportSubmitting}
              >
                {reportSubmitting ? "Analyzing & uploading with AI..." : <><Sparkles size={17} /> Analyze and submit report</>}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* CHATBOT GUIDE */}
      <div className={chatOpen ? "chat-widget open" : "chat-widget"}>
        {chatOpen && (
          <section className="chat-panel">
            <div className="chat-header">
              <div className="chat-avatar">
                <Bot size={18} />
              </div>
              <div>
                <strong>jansethu guide</strong>
                <small>Civic & University Assistant</small>
              </div>
              <button className="icon-button" onClick={() => setChatOpen(false)}>
                <X size={17} />
              </button>
            </div>
            <div className="chat-messages">
              {chatMessages.map((message, index) => (
                <div className={`chat-message ${message.role}`} key={`${message.role}-${index}`}>
                  {message.text}
                </div>
              ))}
            </div>
            <form className="chat-form" onSubmit={sendChat}>
              <input
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                placeholder="Ask about reporting, locations, or universities..."
                aria-label="Ask guide"
              />
              <button type="submit" aria-label="Send message">
                <Send size={16} />
              </button>
            </form>
          </section>
        )}
        <button className="chat-launcher" onClick={() => setChatOpen((prev) => !prev)} aria-label="Open guide">
          <MessageCircle size={20} />
          <span>Need help?</span>
        </button>
      </div>

      <style jsx global>{`
        .modal-backdrop {
          z-index: 1000;
        }
        .modal-backdrop .report-modal {
          position: relative;
          z-index: 1001;
        }
        .map-canvas {
          position: relative;
        }
        .map-canvas > .leaflet-host {
          position: absolute;
          inset: 0;
          z-index: 2;
        }
        .leaflet-host .leaflet-container {
          width: 100%;
          height: 100%;
          border-radius: 7px;
          z-index: 2;
        }
      `}</style>
    </main>
  );
}

type AuthScreenProps = {
  mode: "login" | "register";
  email: string;
  password: string;
  name: string;
  role: string;
  error: string;
  loading: boolean;
  passwordVisible: boolean;
  setMode: (mode: "login" | "register") => void;
  setEmail: (value: string) => void;
  setPassword: (value: string) => void;
  setName: (value: string) => void;
  setRole: (value: string) => void;
  setPasswordVisible: (value: boolean) => void;
  onSubmit: () => void;
};

function AuthScreen({
  mode,
  email,
  password,
  name,
  role,
  error,
  loading,
  passwordVisible,
  setMode,
  setEmail,
  setPassword,
  setName,
  setRole,
  setPasswordVisible,
  onSubmit,
}: AuthScreenProps) {
  const register = mode === "register";
  return (
    <main className="auth-screen">
      <section className="auth-branding">
        <div className="auth-brand-lockup">
          <div className="auth-logo">
            <UsersRound size={28} />
          </div>
          <strong>JAN SETHU</strong>
        </div>
        <div className="auth-brand-copy">
          <p className="auth-eyebrow">CITIZENS · STUDENTS · UNIVERSITIES</p>
          <h1>Small observations can create a bigger, safer tomorrow.</h1>
          <p>Report local problems with photo/video evidence and connect with nearby universities for capstones and research solutions.</p>
        </div>
        <div className="auth-features">
          <div>
            <CheckCircle2 size={19} />
            <span>
              <strong>Citizens & Students</strong>
              <small>Report issues with GPS or map picker</small>
            </span>
          </div>
          <div>
            <GraduationCap size={19} />
            <span>
              <strong>Universities</strong>
              <small>Discover nearby problems for capstones & labs</small>
            </span>
          </div>
          <div>
            <Factory size={19} />
            <span>
              <strong>Civic Impact</strong>
              <small>From local problem to implemented change</small>
            </span>
          </div>
        </div>
        <p className="auth-tagline">FOR A STRONGER TOMORROW</p>
      </section>
      <section className="auth-form-side">
        <div className="auth-form-card">
          <div className="auth-form-heading">
            <div className="auth-form-icon">{register ? <Landmark size={21} /> : <UsersRound size={21} />}</div>
            <p className="auth-eyebrow">JAN SETHU ACCESS</p>
            <h2>{register ? "Create your account" : "Welcome back"}</h2>
            <p>{register ? "Join as Citizen, Student, or University." : "Sign in to continue to JAN SETHU"}</p>
          </div>
          {register && (
            <label>
              Full name / Institution name
              <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Your name or institution" autoComplete="name" />
            </label>
          )}
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email" />
          </label>
          <label>
            Password
            <div className="auth-password-field">
              <input
                type={passwordVisible ? "text" : "password"}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 characters"
                autoComplete={register ? "new-password" : "current-password"}
              />
              <button type="button" onClick={() => setPasswordVisible(!passwordVisible)} aria-label="Toggle password">
                {passwordVisible ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
          </label>
          {register && (
            <label>
              Account type
              <select value={role} onChange={(e) => setRole(e.target.value)}>
                <option value="student">Student (Report & track my events)</option>
                <option value="citizen">Citizen (Report & track my events)</option>
                <option value="university">University (Discover nearby problems for capstones)</option>
                <option value="researcher">Researcher</option>
                <option value="company">Company / Sponsor</option>
                <option value="ngo">NGO</option>
              </select>
            </label>
          )}
          {error && (
            <p className="auth-error" role="alert">
              {error}
            </p>
          )}
          <div className="auth-form-actions" />
          <button className="auth-submit" type="button" onClick={onSubmit} disabled={loading}>
            {loading ? (register ? "Creating account..." : "Signing in...") : register ? "Create account" : "Sign in"}
            <ArrowRight size={17} />
          </button>
          <p className="auth-switch">
            {register ? "Already have an account?" : "Don't have an account?"}{" "}
            <button
              type="button"
              onClick={() => {
                setMode(register ? "login" : "register");
              }}
            >
              {register ? "Sign in" : "Create a new account"}
            </button>
          </p>
        </div>
      </section>
    </main>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <main className="app-shell">
      <section className="content">
        <div className="page-wrap">
          <div className="panel empty-map">{message}</div>
        </div>
      </section>
    </main>
  );
}

function Stat({ icon, label, value, detail, accent }: { icon: React.ReactNode; label: string; value: string; detail: string; accent: string }) {
  return (
    <div className="stat-card">
      <div className={`stat-icon ${accent}`}>{icon}</div>
      <p>{label}</p>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}