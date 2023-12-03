import React, { useEffect, useState } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faArrowUpRightFromSquare } from "@fortawesome/free-solid-svg-icons";
import { toast } from "react-toastify";
import infoLookup from "./infoLookup";
import ReleaseCard from "./ReleaseCard";
import { ToastMsg } from "../../../notifications/Notifications";

interface PanelProps {
  artist: ArtistType;
  onTrackChange: (currentTrack: Array<Listen>) => void;
}

type ArtistInfoType = {
  name?: string;
  type?: string;
  born: string;
  area: string;
  wiki: string;
  mbLink: string;
  topAlbum?: RecordingType | null;
  topTrack: RecordingType | null;
};

// Type for both top track and album i.e. a MB recording.
type RecordingType = {
  release_mbid: string;
  // Release name in case of an album
  release_name: string;
  // Recording name in case of a track
  recording_mbid?: string;
  recording_name?: string;
  caa_id: number;
  caa_release_mbid: string;
};
function Panel({ artist, onTrackChange }: PanelProps) {
  const [artistInfo, setArtistInfo] = useState<ArtistInfoType | null>(null);

  const handleTrackChange = () => {
    if (artistInfo?.topTrack?.recording_name) {
      const newTrack: Array<Listen> = [
        {
          listened_at: 0,
          track_metadata: {
            artist_name: artist.name,
            track_name: artistInfo.topTrack.recording_name,
            release_name: artistInfo.topTrack.release_name,
            release_mbid: artistInfo.topTrack.release_mbid,
            recording_mbid: artistInfo.topTrack.recording_mbid,
          },
        },
      ];
      onTrackChange(newTrack);
    }
  };

  useEffect(() => {
    const getArtistInfo = async () => {
      try {
        const artistApiInfo = await infoLookup(artist.artist_mbid);
        const MB_URL = `https://musicbrainz.org/artist/${artist.artist_mbid}`;
        const newArtistInfo = artistApiInfo;
        // Adding name & type properties to artist info.
        newArtistInfo.name = artist.name;
        newArtistInfo.type = artist.type;
        setArtistInfo(newArtistInfo);
      } catch (error) {
        toast.error(
          <ToastMsg
            title="Search Error"
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "error" }
        );
      }
    };
    getArtistInfo();
  }, [artist]);

  return (
    artistInfo && (
      <div className="artist-panel">
        <div className="artist-panel-header">
          <h2 id="artist-name">{artistInfo.name}</h2>
          <p id="artist-type">{artistInfo.type}</p>
        </div>
        <div className="artist-panel-info">
          <div className="artist-birth-area">
            <strong>Born: </strong>
            {artistInfo.born}
            <br />
            <strong>Area: </strong>
            {artistInfo.area}
          </div>
          <div id="artist-wiki">{artistInfo.wiki}</div>
          <div className="artist-mb-link">
            <a
              id="artist-mb-link-button"
              href={artistInfo.mbLink}
              target="_blank"
              rel="noreferrer"
            >
              <strong>More </strong>
              <FontAwesomeIcon icon={faArrowUpRightFromSquare} />
            </a>
          </div>
        </div>
        {artistInfo.topTrack && (
          <div className="artist-top-album-container">
            <h5>Top Album</h5>
            {/**
             * Needs to be replaced with top album when endpoint is available.
             */}
            {artistInfo.topTrack && (
              <button
                type="button"
                id="artist-top-album"
                onClick={handleTrackChange}
              >
                <ReleaseCard
                  releaseMBID={artistInfo.topTrack.release_mbid}
                  releaseName={artistInfo.topTrack.release_name}
                  caaID={artistInfo.topTrack.caa_id}
                  caaReleaseMBID={artistInfo.topTrack.caa_release_mbid}
                />
              </button>
            )}
          </div>
        )}
        {artistInfo.topTrack && (
          <div className="artist-top-track-container">
            <h5>Top Track</h5>
            {artistInfo.topTrack && (
              <button
                type="button"
                id="artist-top-track"
                onClick={handleTrackChange}
              >
                <ReleaseCard
                  releaseMBID={artistInfo.topTrack.release_mbid}
                  releaseName={artistInfo.topTrack.recording_name ?? "Unknown"}
                  caaID={artistInfo.topTrack.caa_id}
                  caaReleaseMBID={artistInfo.topTrack.caa_release_mbid}
                  recordingMBID={artistInfo.topTrack.recording_mbid}
                />
              </button>
            )}
          </div>
        )}
      </div>
    )
  );
}

export default Panel;
export type { ArtistInfoType, RecordingType };
