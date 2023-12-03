import React, { useCallback, useContext, useEffect, useState } from "react";
import tinycolor from "tinycolor2";
import { toast } from "react-toastify";
import SimilarArtistsGraph from "./SimilarArtistsGraph";
import SearchBox from "./artist-search/SearchBox";
import Panel from "./artist-panel/Panel";
import { ToastMsg } from "../../notifications/Notifications";
import generateTransformedArtists from "./generateTransformedArtists";
import BrainzPlayer from "../../brainzplayer/BrainzPlayer";
import GlobalAppContext from "../../utils/GlobalAppContext";

const ARTIST_MBID = "8f6bd1e4-fbe1-4f50-aa9b-94c450ec0f11";
const SIMILAR_ARTISTS_LIMIT_VALUE = 18;
const BASE_URL =
  "https://labs.api.listenbrainz.org/similar-artists/json?algorithm=session_based_days_7500_session_300_contribution_5_threshold_10_limit_100_filter_True_skip_30&artist_mbid=";
// Apha value of the background color of the graph
const BACKGROUND_ALPHA = 0.2;

const colorGenerator = (): [tinycolor.Instance, tinycolor.Instance] => {
  const initialColor = tinycolor(`hsv(${Math.random() * 360}, 100%, 90%)`);
  return [initialColor, initialColor.clone().tetrad()[1]];
};

function Data() {
  const { APIService } = useContext(GlobalAppContext);

  const [similarArtistsList, setSimilarArtistsList] = useState<
    Array<ArtistType>
  >([]);
  // State to store the complete list of similar artists to help with when user changes artist limit
  const [completeSimilarArtistsList, setCompleteSimilarArtistsList] = useState<
    Array<ArtistType>
  >([]);
  const [mainArtist, setMainArtist] = useState<ArtistType>();
  const [similarArtistsLimit, setSimilarArtistsLimit] = useState(
    SIMILAR_ARTISTS_LIMIT_VALUE
  );
  const [colors, setColors] = useState(colorGenerator);
  const [artistMBID, setArtistMBID] = useState(ARTIST_MBID);
  const [currentTracks, setCurrentTracks] = useState<Array<Listen>>();

  const processData = useCallback((dataResponse: ApiResponseType): void => {
    // Type guard for dataset response
    const isDatasetResponse = (
      response: MarkupResponseType | DatasetResponseType
    ): response is DatasetResponseType => {
      return response.type === "dataset";
    };
    // Get the datasets out of the API response
    const artistsData = dataResponse.filter(isDatasetResponse);
    if (artistsData.length) {
      // Get the main artist from the first dataset
      setMainArtist(artistsData[0]?.data[0]);

      // Get the similar artists from the second dataset
      const similarArtistsResponse = artistsData[1];
      setCompleteSimilarArtistsList(similarArtistsResponse?.data ?? []);
    }
    setColors((prevColors) => [prevColors[1], prevColors[1].tetrad()[1]]);
  }, []);

  const transformedArtists: GraphDataType = mainArtist
    ? generateTransformedArtists(
        mainArtist,
        similarArtistsList,
        colors[0],
        colors[1],
        similarArtistsLimit
      )
    : {
        nodes: [],
        links: [],
      };

  const fetchData = useCallback(
    async (artist_mbid: string): Promise<void> => {
      try {
        const response = await fetch(BASE_URL + artist_mbid);
        const data = await response.json();
        processData(data);
      } catch (error) {
        setSimilarArtistsList([]);
        toast.error(
          <ToastMsg
            title="Search Error"
            message={typeof error === "object" ? error.message : error}
          />,
          { toastId: "error" }
        );
      }
    },
    [processData]
  );

  // Update the graph when either artistMBID or similarArtistsLimit changes
  useEffect(() => {
    fetchData(artistMBID);
  }, [artistMBID, fetchData]);

  // Update the graph when limit changes by only changing the data and not making a new request to server
  useEffect(() => {
    const newSimilarArtistsList = completeSimilarArtistsList.slice(
      0,
      similarArtistsLimit
    );
    setSimilarArtistsList(newSimilarArtistsList);
  }, [completeSimilarArtistsList, similarArtistsLimit]);

  const backgroundColor1 = colors[0]
    .clone()
    .setAlpha(BACKGROUND_ALPHA)
    .toRgbString();

  const backgroundColor2 = colors[1]
    .clone()
    .setAlpha(BACKGROUND_ALPHA)
    .toRgbString();

  const backgroundGradient = `linear-gradient(${
    Math.random() * 360
  }deg ,${backgroundColor1},${backgroundColor2})`;

  return (
    <div className="artist-similarity-main-container">
      <SearchBox
        onArtistChange={setArtistMBID}
        onSimilarArtistsLimitChange={setSimilarArtistsLimit}
        currentSimilarArtistsLimit={similarArtistsLimit}
      />
      <div className="artist-similarity-graph-panel-container">
        <SimilarArtistsGraph
          onArtistChange={setArtistMBID}
          data={transformedArtists}
          background={backgroundGradient}
        />
        {mainArtist && (
          <Panel artist={mainArtist} onTrackChange={setCurrentTracks} />
        )}
      </div>
      <BrainzPlayer
        listens={currentTracks ?? []}
        listenBrainzAPIBaseURI={APIService.APIBaseURI}
        refreshSpotifyToken={APIService.refreshSpotifyToken}
        refreshYoutubeToken={APIService.refreshYoutubeToken}
        refreshSoundcloudToken={APIService.refreshSoundcloudToken}
      />
    </div>
  );
}

export default Data;
